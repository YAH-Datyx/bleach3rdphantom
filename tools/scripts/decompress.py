#!/usr/bin/env python3
"""Dekomprimiert alle Nintendo-komprimierten Dateien (LZ77/Huffman/RLE)
aus unpacked/data/ in unpacked-decomp/data/, Verzeichnisstruktur bleibt erhalten.
Unbekannte/unkomprimierte Dateien werden 1:1 kopiert.
"""
from __future__ import annotations
import shutil, sys
from pathlib import Path
import ndspy.lz10, ndspy.lz11, ndspy.huffman, ndspy.rl

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "unpacked" / "data"
DST  = ROOT / "unpacked-decomp" / "data"

def try_decompress(data: bytes) -> bytes | None:
    if not data:
        return None
    magic = data[0]
    try:
        if magic == 0x10:  return ndspy.lz10.decompress(data)
        if magic == 0x11:  return ndspy.lz11.decompress(data)
        if magic == 0x24 or magic == 0x28:  return ndspy.huffman.decompress(data)
        if magic == 0x30:  return ndspy.rl.decompress(data)
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
            # Kopiere unverändert (war nicht komprimiert oder Fehler)
            shutil.copyfile(p, out)
            if data and data[0] in (0x10, 0x11, 0x24, 0x28, 0x30):
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
