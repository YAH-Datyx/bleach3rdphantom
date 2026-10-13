#!/usr/bin/env python3
"""CRI-CPK-Archive lesen, entpacken und neu bauen (z. B. kuro/c###/c###.cpk).

  python3 tools/re/cpk.py list    unpacked/data/kuro/c001/c001.cpk
  python3 tools/re/cpk.py extract unpacked/data/kuro/c001/c001.cpk build/cpk/c001
  python3 tools/re/cpk.py build   unpacked/data/kuro/c001/c001.cpk build/cpk/c001 out.cpk

Aufbau: "CPK " + @UTF-Header-Tabelle (Big Endian), Inhaltsverzeichnis als
ITOC (Datei-IDs, keine Namen) oder TOC (mit Namen). Dateien liegen ab
ContentOffset, ausgerichtet auf Align. Ist FileSize < ExtractSize, ist die
Datei CRILAYLA-komprimiert (hier mit genullter Signatur).
Beim Bauen werden Dateien unkomprimiert abgelegt (FileSize == ExtractSize),
alle anderen Tabellenwerte bleiben erhalten.
"""
from __future__ import annotations
import struct, sys
from pathlib import Path

# --- @UTF-Tabellen ------------------------------------------------------------

TYPES = {0: ">B", 1: ">b", 2: ">H", 3: ">h", 4: ">I", 5: ">i", 6: ">Q", 7: ">q", 8: ">f"}
STORE_ZERO, STORE_CONST, STORE_ROW = 0x10, 0x30, 0x50


def _read_value(t: int, buf: bytes, pos: int, strings: int, data: int, base: bytes):
    if t in TYPES:
        fmt = TYPES[t]
        return struct.unpack_from(fmt, buf, pos)[0], pos + struct.calcsize(fmt)
    if t == 0xA:
        o = struct.unpack_from(">I", buf, pos)[0]
        end = base.index(b"\0", strings + o)
        return base[strings + o:end].decode("ascii", "replace"), pos + 4
    if t == 0xB:
        o, n = struct.unpack_from(">II", buf, pos)
        return base[data + o:data + o + n], pos + 8
    raise ValueError(f"unbekannter @UTF-Typ {t:#x}")


def parse_utf(blob: bytes) -> dict:
    if blob[:4] != b"@UTF":
        raise ValueError("kein @UTF")
    size = struct.unpack_from(">I", blob, 4)[0]
    t = blob[8:8 + size]
    _, rows_off, str_off, data_off, name_off, ncol, row_len, nrows = struct.unpack_from(">HHIIIHHI", t, 0)
    name = t[str_off + name_off:t.index(b"\0", str_off + name_off)].decode()
    cols, pos = [], 24
    for _ in range(ncol):
        flags = t[pos]
        cname_off = struct.unpack_from(">I", t, pos + 1)[0]
        pos += 5
        cname = t[str_off + cname_off:t.index(b"\0", str_off + cname_off)].decode()
        const = None
        if flags & 0xF0 == STORE_CONST:
            const, pos = _read_value(flags & 0x0F, t, pos, str_off, data_off, t)
        cols.append((cname, flags, const))
    rows = []
    for r in range(nrows):
        p = rows_off + r * row_len
        row = {}
        for cname, flags, const in cols:
            st = flags & 0xF0
            if st == STORE_ROW:
                row[cname], p = _read_value(flags & 0x0F, t, p, str_off, data_off, t)
            elif st == STORE_CONST:
                row[cname] = const
            else:
                row[cname] = None
        rows.append(row)
    return {"name": name, "columns": cols, "rows": rows, "_raw": t}


def patch_utf_cells(blob: bytes, row: int, values: dict) -> bytes:
    """Ändert Zahlenwerte einer Zeile in-place (nur Spalten mit Per-Zeile-Speicherung)."""
    size = struct.unpack_from(">I", blob, 4)[0]
    t = bytearray(blob[8:8 + size])
    _, rows_off, str_off, data_off, name_off, ncol, row_len, nrows = struct.unpack_from(">HHIIIHHI", t, 0)
    pos, layout = 24, []
    for _ in range(ncol):
        flags = t[pos]
        cname_off = struct.unpack_from(">I", t, pos + 1)[0]
        pos += 5
        cname = t[str_off + cname_off:t.index(b"\0", str_off + cname_off)].decode()
        const = None
        if flags & 0xF0 == STORE_CONST:
            const, pos = _read_value(flags & 0x0F, t, pos, str_off, data_off, t)
        layout.append((cname, flags, const))
    p = rows_off + row * row_len
    for cname, flags, const in layout:
        typ = flags & 0x0F
        if flags & 0xF0 != STORE_ROW:
            if cname in values and values[cname] != (const if flags & 0xF0 == STORE_CONST else None):
                raise ValueError(f"Spalte {cname} ist nicht pro Zeile gespeichert, Wert nicht änderbar")
            continue
        width = 4 if typ == 0xA else 8 if typ == 0xB else struct.calcsize(TYPES[typ])
        if cname in values:
            struct.pack_into(TYPES[typ], t, p, values[cname])
        p += width
    return blob[:8] + bytes(t) + blob[8 + size:]


# --- CRILAYLA -------------------------------------------------------------------

def decompress_crilayla(src: bytes) -> bytes:
    """CRILAYLA: Bitstream wird von hinten gelesen, Ausgabe von hinten gefüllt;
    die ersten 0x100 Bytes stehen unkomprimiert am Ende.

    In dieser ROM ist die Signatur "CRILAYLA" durch 8 Nullbytes ersetzt; erkannt
    wird das Format deshalb an FileSize < ExtractSize (siehe file_data).
    """
    usize, hoff = struct.unpack_from("<II", src, 8)
    if hoff + 0x110 != len(src):
        raise ValueError("kein CRILAYLA-Layout")
    prefix = src[hoff + 0x10:hoff + 0x10 + 0x100]
    out = bytearray(usize)
    pos = hoff + 0x10 - 1          # Bitstream: letztes Byte vor dem Prefix, rückwärts
    bit_pool = bits_left = 0
    written = 0

    def get(n):
        nonlocal pos, bit_pool, bits_left
        v = 0
        while n:
            if bits_left == 0:
                bit_pool = src[pos]; pos -= 1; bits_left = 8
            take = min(bits_left, n)
            v = (v << take) | ((bit_pool >> (bits_left - take)) & ((1 << take) - 1))
            bits_left -= take; n -= take
        return v

    end = usize - 1
    while written < usize:
        if get(1):
            back = get(13) + 3
            length = 3
            for lvl in (2, 3, 5):
                add = get(lvl)
                length += add
                if add != (1 << lvl) - 1:
                    break
            else:
                while True:
                    add = get(8)
                    length += add
                    if add != 0xFF:
                        break
            for _ in range(length):
                out[end - written] = out[end - written + back]
                written += 1
        else:
            out[end - written] = get(8)
            written += 1
    return bytes(prefix) + bytes(out)


# --- CPK ------------------------------------------------------------------------

def read_cpk(path: Path) -> dict:
    b = path.read_bytes()
    if b[:4] != b"CPK ":
        raise ValueError("kein CPK")
    head = parse_utf(b[0x10:])
    h = head["rows"][0]
    files = []
    content, align = h.get("ContentOffset") or 0, h.get("Align") or 1
    if h.get("ItocOffset"):
        itoc = parse_utf(b[h["ItocOffset"] + 0x10:])
        r = itoc["rows"][0]
        entries = []
        for key in ("DataL", "DataH"):
            if r.get(key):
                entries += parse_utf(r[key])["rows"]
        entries.sort(key=lambda e: e["ID"])
        off = content
        for e in entries:
            files.append({"id": e["ID"], "offset": off, "size": e["FileSize"], "extract": e["ExtractSize"]})
            off += e["FileSize"]
            off = (off + align - 1) // align * align
    elif h.get("TocOffset"):
        toc = parse_utf(b[h["TocOffset"] + 0x10:])
        base = min(h["TocOffset"], content) if content else h["TocOffset"]
        for i, e in enumerate(toc["rows"]):
            name = "/".join(x for x in (e.get("DirName"), e.get("FileName")) if x)
            files.append({"id": e.get("ID", i), "name": name, "offset": base + e["FileOffset"],
                          "size": e["FileSize"], "extract": e["ExtractSize"]})
    return {"header": h, "files": files, "_bytes": b}


def file_data(cpk: dict, f: dict) -> bytes:
    raw = cpk["_bytes"][f["offset"]:f["offset"] + f["size"]]
    return decompress_crilayla(raw) if f["size"] < f["extract"] else raw


def _utf_data_cells(blob: bytes, row: int = 0) -> dict:
    """Position (relativ zum Blob) und Größe der Daten-Zellen (Typ 0xB) einer Zeile."""
    t = blob[8:]
    _, rows_off, str_off, data_off, _, ncol, row_len, _ = struct.unpack_from(">HHIIIHHI", t, 0)
    pos, out = 24, {}
    p = rows_off + row * row_len
    for _ in range(ncol):
        flags = t[pos]
        cname_off = struct.unpack_from(">I", t, pos + 1)[0]
        pos += 5
        cname = t[str_off + cname_off:t.index(b"\0", str_off + cname_off)].decode()
        typ = flags & 0x0F
        if flags & 0xF0 == STORE_CONST:
            _, pos = _read_value(typ, t, pos, str_off, data_off, t)
        if flags & 0xF0 == STORE_ROW:
            if typ == 0xB:
                o, n = struct.unpack_from(">II", t, p)
                out[cname] = (8 + data_off + o, n)
            p += 4 if typ == 0xA else 8 if typ == 0xB else struct.calcsize(TYPES[typ])
    return out


def build_cpk(cpk: dict, replace: dict[int, bytes]) -> bytes:
    """Baut das CPK neu. Ersetzte Dateien werden unkomprimiert abgelegt."""
    b = cpk["_bytes"]
    h = cpk["header"]
    if not h.get("ItocOffset"):
        raise ValueError("nur ITOC-CPKs werden unterstützt")
    align, content = h["Align"] or 1, h["ContentOffset"]
    body = bytearray(b[:content])
    sizes = {}
    for f in cpk["files"]:
        raw = replace.get(f["id"])
        if raw is None:
            raw = b[f["offset"]:f["offset"] + f["size"]]
            sizes[f["id"]] = (f["size"], f["extract"])
        else:
            sizes[f["id"]] = (len(raw), len(raw))
        body += raw
        body += bytes((-len(body)) % align)
    # ITOC-Block (16-Byte-Chunkheader + @UTF) übernehmen und Größen patchen
    ioff, isize = h["ItocOffset"], h["ItocSize"]
    itoc = bytearray(b[ioff:ioff + isize])
    cells = _utf_data_cells(bytes(itoc[0x10:]))
    for key, (pos, n) in cells.items():
        if key not in ("DataL", "DataH") or not n:
            continue
        start = 0x10 + pos
        nested = bytes(itoc[start:start + n])
        table = parse_utf(nested)
        for r, e in enumerate(table["rows"]):
            fs, es = sizes[e["ID"]]
            if key == "DataL" and max(fs, es) > 0xFFFF:
                raise ValueError(f"Datei {e['ID']} ist für DataL (u16) zu groß")
            nested = patch_utf_cells(nested, r, {"FileSize": fs, "ExtractSize": es})
        itoc[start:start + n] = nested
    new_ioff = len(body)
    body += itoc
    body += b[ioff + isize:]
    # Nur ItocOffset ändert sich. EnabledPackedSize/EnabledDataSize sind Statistikwerte,
    # die mit den Dateigrößen nicht übereinstimmen; sie bleiben wie im Original.
    head = patch_utf_cells(bytes(body[0x10:]), 0, {"ItocOffset": new_ioff})
    body[0x10:0x10 + len(head)] = head
    return bytes(body)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, path = argv[1], Path(argv[2])
    cpk = read_cpk(path)
    if cmd == "list":
        for f in cpk["files"]:
            d = file_data(cpk, f)
            print(f"id {f['id']:4d}  @{f['offset']:#08x}  {f['size']:7d} → {f['extract']:7d}  {d[:4]!r}")
    elif cmd == "extract":
        out = Path(argv[3])
        out.mkdir(parents=True, exist_ok=True)
        for f in cpk["files"]:
            (out / f"{f['id']:04d}.bin").write_bytes(file_data(cpk, f))
        print(f"{len(cpk['files'])} Dateien → {out}")
    elif cmd == "build":
        src, out = Path(argv[3]), Path(argv[4])
        repl = {}
        for f in cpk["files"]:
            p = src / f"{f['id']:04d}.bin"
            if p.exists() and p.read_bytes() != file_data(cpk, f):
                repl[f["id"]] = p.read_bytes()
        out.write_bytes(build_cpk(cpk, repl))
        print(f"{len(repl)} Datei(en) ersetzt → {out}")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
