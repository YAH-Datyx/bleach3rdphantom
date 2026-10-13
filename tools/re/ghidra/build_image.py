#!/usr/bin/env python3
"""Baut ein flaches RAM-Abbild arm9 (+ ein Overlay) ab 0x02000000 für Ghidra.

  python3 tools/re/ghidra/build_image.py <overlay-nr> <out.bin>
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE, OVL_BASE = 0x02000000, 0x0215B5A0

ov, out = int(sys.argv[1]), Path(sys.argv[2])
img = bytearray((ROOT / "unpacked" / "arm9.bin").read_bytes())
img += bytes(OVL_BASE - BASE - len(img))
img += (ROOT / "unpacked" / "overlay" / f"overlay_{ov:04d}.bin").read_bytes()
out.write_bytes(img)
print(f"{out}: {len(img):#x} Bytes, Overlay {ov} @ {OVL_BASE:#x}")
