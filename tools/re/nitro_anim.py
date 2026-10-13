#!/usr/bin/env python3
"""Parser + Writer für Nitro-Zellen (NCER) und -Animationen (NANR).

Beide Formate werden in Python-Dicts übersetzt (JSON-tauglich) und daraus
wieder byte-genau zurückgebaut. Damit lassen sich Animationen umbauen
(Frames, Dauer, Reihenfolge, Positionen, neue Sequenzen) und Zellen ändern
(OAM-Objekte: Position, Größe, Tile, Palette, Flip).

Layout (verifiziert an allen NCER/NANR der ROM, siehe tests/test_nitro_anim.py):

NCER  Header(16) | KBEC | [LBAL] [TXEU] ...
  KBEC: u16 nCells, u16 bankType (0: Zelle 8 B, 1: 16 B mit Bounds),
        u32 cellsOff, u32 mapping, u32 vramOff, u32 pad, u32 extOff
        Zelle: u16 nOAM, u16 attr, u32 oamOff [s16 xMax yMax xMin yMin]
        OAM: 3 × u16 (attr0/1/2 wie DS-Hardware)
        VRAM-Transfer (vramOff != 0): u32 maxSize, u32 8, je Zelle (u32 off, u32 size)
NANR  Header(16) | KNBA | [LBAL] [TXEU] ...
  KNBA: u16 nSeq, u16 nFrames, u32 seqOff, u32 frameOff, u32 dataOff, 8 B pad
        Sequenz (16 B): u16 nFrames, u16 loopStart, u16 elemType, u16 animType,
                        u32 playMode, u32 frameOff
        Frame (8 B): u32 dataOff, u16 duration, u16 pad (0xBEEF)
        Element: Typ 0 = u16 cell; Typ 1 = cell, rot, s32 sx, s32 sy, s16 tx, ty;
                 Typ 2 = cell, u16 pad, s16 x, s16 y
LBAL: u32-Offsets, dann nullterminierte Namen (Sequenz- bzw. Zellnamen)
"""
from __future__ import annotations
import struct

ELEM_FMT = {0: "<H", 1: "<HHiihh", 2: "<HHhh"}
ELEM_KEYS = {0: ("cell",), 1: ("cell", "rot", "sx", "sy", "tx", "ty"), 2: ("cell", "pad", "x", "y")}


# --- Nitro-Container --------------------------------------------------------

def split_sections(data: bytes) -> tuple[bytes, list[tuple[bytes, bytes]], bytes]:
    hsize = struct.unpack_from("<H", data, 0x0C)[0]
    nsec = struct.unpack_from("<H", data, 0x0E)[0]
    pos, out = hsize, []
    for _ in range(nsec):
        magic, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        out.append((magic, data[pos + 8:pos + size]))
        pos += size
    return data[:hsize], out, data[pos:]   # Rest = Padding nach dem letzten Abschnitt


def join_sections(header: bytes, sections: list[tuple[bytes, bytes]], trail: bytes = b"") -> bytes:
    body = b"".join(m + struct.pack("<I", len(c) + 8) + c for m, c in sections) + trail
    h = bytearray(header)
    struct.pack_into("<I", h, 8, len(h) + len(body))
    struct.pack_into("<H", h, 0x0E, len(sections))
    return bytes(h) + body


def parse_labels(content: bytes) -> list[str]:
    """LBAL: u32-Offset-Tabelle, danach nullterminierte Strings.

    Die Tabelle endet, sobald ein Wert kein plausibler Offset mehr ist (dort
    beginnen die ASCII-Strings). Die Namen dienen nur zur Anzeige; das Original
    LBAL wird beim Bauen unverändert übernommen.
    """
    offs = []
    while 4 * len(offs) + 4 <= len(content):
        o = struct.unpack_from("<I", content, 4 * len(offs))[0]
        if o >= len(content):
            break
        offs.append(o)
    base = 4 * len(offs)
    names = []
    for o in offs:
        end = content.find(b"\0", base + o)
        names.append(content[base + o:end if end >= 0 else None].decode("ascii", "replace"))
    return names


# --- NCER -------------------------------------------------------------------

def parse_ncer(data: bytes) -> dict:
    header, sections, trail = split_sections(data)
    kbec = sections[0][1]
    n, bank, coff, mapping, voff, pad, eoff = struct.unpack_from("<HHIIIII", kbec, 0)
    csize = 16 if bank == 1 else 8
    oam_base = coff + n * csize
    cells = []
    for i in range(n):
        noam, attr, ooff = struct.unpack_from("<HHI", kbec, coff + i * csize)
        c = {"attr": attr, "oam": []}
        if bank == 1:
            c["bounds"] = list(struct.unpack_from("<4h", kbec, coff + i * csize + 8))
        for k in range(noam):
            a0, a1, a2 = struct.unpack_from("<3H", kbec, oam_base + ooff + k * 6)
            c["oam"].append(decode_oam(a0, a1, a2))
        c["_oam_off"] = ooff
        cells.append(c)
    oam_end = oam_base + max((c["_oam_off"] + 6 * len(c["oam"]) for c in cells), default=0)
    out = {"bank_type": bank, "mapping": mapping, "pad": pad, "ext_off": eoff, "cells": cells,
           "_header": header.hex(), "_trail": trail.hex()}
    tail_start = oam_end
    if voff:
        maxsize, toff = struct.unpack_from("<II", kbec, voff)
        out["vram"] = {"max_size": maxsize, "table_off": toff,
                       "cells": [list(struct.unpack_from("<II", kbec, voff + toff + i * 8)) for i in range(n)]}
        out["_gap"] = kbec[oam_end:voff].hex()
        tail_start = voff + toff + n * 8
    out["_tail"] = kbec[tail_start:].hex()
    out["_sections"] = [(m.decode(), c.hex()) for m, c in sections[1:]]
    labels = [c for m, c in sections[1:] if m == b"LBAL"]
    if labels:
        try:
            out["labels"] = parse_labels(labels[0])
        except Exception:
            pass
    return out


def build_ncer(obj: dict) -> bytes:
    cells = obj["cells"]
    bank = obj["bank_type"]
    csize = 16 if bank == 1 else 8
    coff = 0x18
    table = bytearray()
    oam = bytearray()
    seen: dict[bytes, int] = {}
    for c in cells:
        blob = b"".join(struct.pack("<3H", *encode_oam(o)) for o in c["oam"])
        # gleiche OAM-Listen teilen sich Daten nur, wenn das Original es auch tat
        ooff = c.get("_oam_off")
        if ooff is None or ooff > len(oam) or (ooff < len(oam) and oam[ooff:ooff + len(blob)] != blob):
            ooff = seen.get(blob, len(oam)) if blob in seen else len(oam)
        if ooff == len(oam):
            seen.setdefault(blob, ooff)
            oam += blob
        table += struct.pack("<HHI", len(c["oam"]), c["attr"], ooff)
        if bank == 1:
            table += struct.pack("<4h", *c.get("bounds", cell_bounds(c)))
    body = bytearray(table + oam)
    voff = 0
    if "vram" in obj:
        body += bytes.fromhex(obj.get("_gap", ""))
        voff = coff + len(body)
        v = obj["vram"]
        body += struct.pack("<II", v["max_size"], v["table_off"])
        body += bytes(max(0, v["table_off"] - 8))
        for off, size in v["cells"]:
            body += struct.pack("<II", off, size)
    body += bytes.fromhex(obj.get("_tail", ""))
    kbec = struct.pack("<HHIIIII", len(cells), bank, coff, obj["mapping"], voff,
                       obj.get("pad", 0), obj.get("ext_off", 0)) + bytes(body)
    secs = [(b"KBEC", kbec)] + [(m.encode(), bytes.fromhex(c)) for m, c in obj.get("_sections", [])]
    return join_sections(bytes.fromhex(obj["_header"]), secs, bytes.fromhex(obj.get("_trail", "")))


# --- OAM --------------------------------------------------------------------

SIZES = {  # (shape, size) -> (w, h)
    (0, 0): (8, 8), (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
    (1, 0): (16, 8), (1, 1): (32, 8), (1, 2): (32, 16), (1, 3): (64, 32),
    (2, 0): (8, 16), (2, 1): (8, 32), (2, 2): (16, 32), (2, 3): (32, 64),
}


def decode_oam(a0: int, a1: int, a2: int) -> dict:
    y = a0 & 0xFF
    x = a1 & 0x1FF
    shape, size = a0 >> 14, a1 >> 14
    w, h = SIZES.get((shape, size), (8, 8))
    rs = bool(a0 & 0x100)
    o = {
        "x": x - 512 if x >= 256 else x, "y": y - 256 if y >= 128 else y,
        "w": w, "h": h, "tile": a2 & 0x3FF, "palette": a2 >> 12, "priority": a2 >> 10 & 3,
        "bpp8": bool(a0 & 0x2000), "hflip": bool(not rs and a1 & 0x1000),
        "vflip": bool(not rs and a1 & 0x2000),
    }
    # Restbits unverändert mitführen (Rotation/Scaling, Modus, Mosaik …)
    o["_a0"] = a0 & ~(0xFF | 0xC000 | 0x2000)
    o["_a1"] = a1 & ~(0x1FF | 0xC000 | (0 if rs else 0x3000))
    return o


def encode_oam(o: dict) -> tuple[int, int, int]:
    shape, size = next(k for k, v in SIZES.items() if v == (o["w"], o["h"]))
    a0 = (o["y"] & 0xFF) | shape << 14 | (0x2000 if o["bpp8"] else 0) | o.get("_a0", 0)
    a1 = (o["x"] & 0x1FF) | size << 14 | o.get("_a1", 0)
    if not a0 & 0x100:
        a1 |= (0x1000 if o["hflip"] else 0) | (0x2000 if o["vflip"] else 0)
    a2 = (o["tile"] & 0x3FF) | (o["priority"] & 3) << 10 | (o["palette"] & 15) << 12
    return a0, a1, a2


def cell_bounds(c: dict) -> list[int]:
    if not c["oam"]:
        return [0, 0, 0, 0]
    return [max(o["x"] + o["w"] for o in c["oam"]), max(o["y"] + o["h"] for o in c["oam"]),
            min(o["x"] for o in c["oam"]), min(o["y"] for o in c["oam"])]


# --- NANR -------------------------------------------------------------------

def parse_nanr(data: bytes) -> dict:
    header, sections, trail = split_sections(data)
    k = sections[0][1]
    nseq, nfr, soff, foff, doff = struct.unpack_from("<HHIII", k, 0)
    seqs = []
    data_end = doff
    for i in range(nseq):
        n, loop, et, at, mode, sfo = struct.unpack_from("<HHHHII", k, soff + i * 16)
        frames = []
        for j in range(n):
            eoff, dur, pad = struct.unpack_from("<IHH", k, foff + sfo + j * 8)
            fmt = ELEM_FMT[et]
            vals = struct.unpack_from(fmt, k, doff + eoff)
            data_end = max(data_end, doff + eoff + struct.calcsize(fmt))
            frames.append({"duration": dur, **dict(zip(ELEM_KEYS[et], vals)),
                           "_data_off": eoff, "_pad": pad})
        seqs.append({"loop_start": loop, "elem_type": et, "anim_type": at, "play_mode": mode,
                     "frames": frames, "_frame_off": sfo})
    out = {"sequences": seqs, "_header": header.hex(), "_trail": trail.hex(),
           "_knba_pad": k[0x10:soff].hex(),
           "_sections": [(m.decode(), c.hex()) for m, c in sections[1:]]}
    # Frame-Daten werden beim Bauen neu erzeugt; Original-Bytes für exaktes Round-Trip
    out["_data"] = k[doff:].hex()
    labels = [c for m, c in sections[1:] if m == b"LBAL"]
    if labels:
        try:
            out["labels"] = parse_labels(labels[0])
        except Exception:
            pass
    return out


def build_nanr(obj: dict) -> bytes:
    seqs = obj["sequences"]
    nfr = sum(len(s["frames"]) for s in seqs)
    soff = 0x10 + len(bytes.fromhex(obj.get("_knba_pad", "0000000000000000")))
    foff = soff + 16 * len(seqs)
    doff = foff + 8 * nfr
    orig = bytes.fromhex(obj.get("_data", ""))
    data = bytearray()
    ftab = bytearray()
    stab = bytearray()
    reuse_ok = bool(orig)
    # Prüfen, ob die Original-Framedaten noch zu allen Frames passen → dann 1:1
    for s in seqs:
        fmt = ELEM_FMT[s["elem_type"]]
        for f in s["frames"]:
            o = f.get("_data_off")
            vals = tuple(f[key] for key in ELEM_KEYS[s["elem_type"]])
            if o is None or o + struct.calcsize(fmt) > len(orig) or struct.unpack_from(fmt, orig, o) != vals:
                reuse_ok = False
    if reuse_ok:
        data = bytearray(orig)
    for s in seqs:
        fmt = ELEM_FMT[s["elem_type"]]
        stab += struct.pack("<HHHHII", len(s["frames"]), s["loop_start"], s["elem_type"],
                            s["anim_type"], s["play_mode"], len(ftab))
        local: dict[tuple, int] = {}
        for f in s["frames"]:
            vals = tuple(f[key] for key in ELEM_KEYS[s["elem_type"]])
            if reuse_ok:
                eoff = f["_data_off"]
            else:
                if vals not in local:
                    local[vals] = len(data)
                    data += struct.pack(fmt, *vals)
                eoff = local[vals]
            ftab += struct.pack("<IHH", eoff, f["duration"], f.get("_pad", 0xBEEF))
        if not reuse_ok:
            while len(data) % 4:
                data += b"\xcc"
    k = (struct.pack("<HHIII", len(seqs), nfr, soff, foff, doff)
         + bytes.fromhex(obj.get("_knba_pad", "0000000000000000")) + stab + ftab + data)
    secs = [(b"KNBA", k)] + [(m.encode(), bytes.fromhex(c)) for m, c in obj.get("_sections", [])]
    return join_sections(bytes.fromhex(obj["_header"]), secs, bytes.fromhex(obj.get("_trail", "")))
