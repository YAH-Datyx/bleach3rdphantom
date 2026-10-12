#!/usr/bin/env python3
"""Dekomprimiert Nintendo-komprimierte Dateien (LZ10/LZ11, Huffman 4/8-bit)
aus unpacked/data/ in unpacked-decomp/data/, Verzeichnisstruktur bleibt erhalten.
Unkomprimierte/unbekannte Dateien werden 1:1 kopiert.
Spezifikation: GBATEK BIOS Decompression Functions (SWI 13h).
"""
from __future__ import annotations
import shutil, sys, struct
from pathlib import Path
import ndspy.lz10

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "unpacked" / "data"
DST  = ROOT / "unpacked-decomp" / "data"


def decompress_huffman(data: bytes) -> bytes:
    """Nintendo Huffman 0x24 (4-bit) / 0x28 (8-bit), nach GBATEK (SWI 13h).

    Baum ab data[4]: Größenbyte, dann Wurzel bei data[5]. Innerer Knoten:
    Bits 0-5 = Offset, Bit 7/6 = Kind 0/1 ist Blatt. Das Kinder-Paar liegt bei
    (Adresse AND NOT 1) + Offset*2 + 2, mit absoluten Adressen (data[4] ist
    4-Byte-aligned, deshalb zählt die Parität des absoluten Offsets).
    Bitstream: 32-Bit-LE-Wörter, MSB zuerst. 4-bit: erstes Nibble = low nibble.
    """
    header = data[0]
    bit_size = header & 0x0F
    if header >> 4 != 2 or bit_size not in (4, 8):
        raise ValueError(f"kein Huffman: 0x{header:02X}")
    dec_size = data[1] | (data[2] << 8) | (data[3] << 16)
    root = 5
    pos = 4 + (data[4] + 1) * 2               # Bitstream nach Header + Baum

    out = bytearray()
    nibble = -1
    node = root
    n = len(data)
    while len(out) < dec_size:
        if pos + 4 > n:
            raise ValueError("Bitstream zu kurz")
        word = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        for shift in range(31, -1, -1):
            bit = (word >> shift) & 1
            parent = data[node]
            child = (node & ~1) + (parent & 0x3F) * 2 + 2 + bit
            if child >= n:
                raise ValueError("Baum-Index außerhalb der Daten")
            if parent & (0x80 >> bit):
                value = data[child]
                node = root
                if bit_size == 8:
                    out.append(value)
                elif nibble < 0:
                    nibble = value & 0x0F
                else:
                    out.append((value & 0x0F) << 4 | nibble)
                    nibble = -1
                if len(out) >= dec_size:
                    break
            else:
                node = child
    return bytes(out)


def try_decompress(data: bytes) -> bytes | None:
    if not data:
        return None
    magic = data[0]
    try:
        if magic in (0x10, 0x11):
            return ndspy.lz10.decompress(data)
        if magic in (0x24, 0x28):
            return decompress_huffman(data)
    except Exception:
        return None
    return None


def main() -> int:
    if not SRC.exists():
        print(f"Quelle fehlt: {SRC}", file=sys.stderr); return 1
    n_decomp = n_copy = n_fail = 0
    for p in SRC.rglob("*"):
        if not p.is_file(): continue
        rel = p.relative_to(SRC)
        out = DST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        decomp = try_decompress(data)
        if decomp is not None:
            out.write_bytes(decomp)
            n_decomp += 1
        else:
            shutil.copyfile(p, out)
            if data and data[0] in (0x10, 0x11, 0x24, 0x28):
                n_fail += 1
            else:
                n_copy += 1
    print(f"Dekomprimiert: {n_decomp}")
    print(f"Kopiert (unkomprimiert): {n_copy}")
    print(f"Fehlgeschlagen (Magic gesetzt, decomp Fehler): {n_fail}")
    print(f"Output: {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
