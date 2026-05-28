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
    """Nintendo Huffman 0x24 (4-bit) / 0x28 (8-bit) Decompressor.
    Portiert nach DSDecmp / CUE's Nintendo Decompressor."""
    header = data[0]
    bit_size = header & 0x0F
    if bit_size not in (4, 8):
        raise ValueError(f"kein Huffman: 0x{header:02X}")
    dec_size = data[1] | (data[2] << 8) | (data[3] << 16)
    tree_size = (data[4] + 1) << 1            # gesamte Tree-Größe in Bytes (inkl. das erste Größen-Byte)
    tree_root = 5                              # Root-Knoten direkt nach dem Größen-Byte
    bs_off   = 4 + tree_size                   # Bitstream beginnt nach Header + Tree

    out = bytearray()
    nibble_buf = -1                            # für 4-bit-Modus
    node = tree_root
    bits_left = 0
    word = 0
    pos = bs_off
    n = len(data)

    while len(out) < dec_size:
        if bits_left == 0:
            if pos + 4 > n:
                break
            word = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            bits_left = 32
        bit = (word >> 31) & 1
        word = (word << 1) & 0xFFFFFFFF
        bits_left -= 1

        parent = data[node]
        # Adresse des Kinder-Paares
        next_pair = ((node - tree_root) & ~1) + (parent & 0x3F) * 2 + 2 + tree_root
        child = next_pair + bit
        is_leaf = (parent & (0x80 >> bit)) != 0
        node = child

        if is_leaf:
            value = data[node]
            if bit_size == 8:
                out.append(value)
            else:  # 4-bit: zwei Nibbles pro Output-Byte, low nibble zuerst
                if nibble_buf < 0:
                    nibble_buf = value & 0x0F
                else:
                    out.append((value & 0x0F) << 4 | nibble_buf)
                    nibble_buf = -1
            node = tree_root

    return bytes(out[:dec_size])


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
