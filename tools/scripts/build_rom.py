#!/usr/bin/env python3
"""Baut aus Original-ROM + unpacked/ eine gepatchte ROM (reines Python, ndspy).

Übernommen werden arm9.bin, arm7.bin, overlay/overlay_XXXX.bin und alle Dateien
unter unpacked/data, die sich vom Original unterscheiden. Neue Dateien legt das
Skript nicht an: Das Spiel lädt Dateien über feste Namen bzw. IDs, und eine neue
Datei braucht auch Code oder Daten, die sie referenzieren.

  python3 tools/scripts/build_rom.py [rom/Bleach3rdPhantom.nds] [build/Bleach3rdPhantom.patched.nds]
"""
import sys
from pathlib import Path

import ndspy.rom

ROOT = Path(__file__).resolve().parents[2]
UNPACKED = ROOT / "unpacked"


def build(base: Path, out: Path, unpacked: Path = UNPACKED) -> list[str]:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(base))
    changed = []
    for name, attr in (("arm9.bin", "arm9"), ("arm7.bin", "arm7")):
        new = (unpacked / name).read_bytes()
        if new != getattr(rom, attr):
            setattr(rom, attr, new)
            changed.append(name)
    for i, ov in rom.loadArm9Overlays().items():
        p = unpacked / "overlay" / f"overlay_{i:04d}.bin"
        if p.exists() and p.read_bytes() != ov.data:
            rom.files[ov.fileID] = p.read_bytes()
            changed.append(p.name)
    for fid in range(len(rom.files)):
        name = rom.filenames.filenameOf(fid)
        if name is None:
            continue
        p = unpacked / "data" / name
        if p.exists():
            new = p.read_bytes()
            if new != rom.files[fid]:
                rom.files[fid] = new
                changed.append(name)
    out.parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    return changed


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "rom" / "Bleach3rdPhantom.nds"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build" / "Bleach3rdPhantom.patched.nds"
    ch = build(base, out)
    print(f"{len(ch)} geänderte Datei(en): {', '.join(ch[:10])}{' …' if len(ch) > 10 else ''}")
    print(f"→ {out}")
