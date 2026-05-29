#!/usr/bin/env python3
"""Schnell-Test mehrerer Char-IDs auf Floor 9.

Usage:
  ./tools/scripts/test_ids.py 209 221 244 246

Patcht Slots 21, 22, 23, 24 mit den 4 angegebenen IDs (Lv 88), repackt,
kopiert ROM zum Windows-Desktop. Danach nur noch ROM in DeSmuME neu öffnen.
"""
import sys, struct, subprocess, shutil
from pathlib import Path
import ndspy.narc

ROOT = Path(__file__).resolve().parents[2]
NARC = ROOT / "unpacked" / "data" / "yamada" / "DataBase" / "db_dpos_909.narc"
BUILD = ROOT / "build" / "Bleach3rdPhantom.patched.nds"
DESKTOP = Path("/mnt/c/Users/danie/OneDrive - Technische Hochschule Rosenheim/Desktop/Bleach - The 3rd Phantom (Europe) (EnFr)")

ENTRY = 54
TEST_SLOTS = [21, 22, 23, 24]  # 4 Slots auf Floor 9 für Tests

def main():
    if len(sys.argv) < 5:
        sys.exit(f"Usage: {sys.argv[0]} ID1 ID2 ID3 ID4")
    ids = [int(x) for x in sys.argv[1:5]]

    # 1. Patch NARC
    narc = ndspy.narc.NARC.fromFile(str(NARC))
    f0 = bytearray(narc.files[0])
    for slot, cid in zip(TEST_SLOTS, ids):
        off = slot * ENTRY
        struct.pack_into('<H', f0, off+2, cid)
        struct.pack_into('<H', f0, off+4, 88)
        print(f"  Slot {slot}: char_id={cid} lvl=88")
    narc.files[0] = bytes(f0)
    narc.saveToFile(str(NARC))

    # 2. Repack
    print("\nRepack...")
    subprocess.run([str(ROOT / "tools" / "repack.sh")], check=True, cwd=ROOT)

    # 3. Copy to Windows
    shutil.copy(BUILD, DESKTOP)
    print(f"\n✓ ROM kopiert: {DESKTOP / BUILD.name}")
    print("→ In DeSmuME: File→Close, File→Open, Floor 9")

if __name__ == '__main__':
    main()
