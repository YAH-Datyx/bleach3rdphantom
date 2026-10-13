#!/usr/bin/env python3
"""Entpackt eine .nds rein in Python (ndspy) — Alternative zu tools/unpack.sh ohne ndstool.

  python3 tools/scripts/unpack_rom.py [rom/Bleach3rdPhantom.nds] [unpacked]

Layout wie bei ndstool -x: arm9.bin, arm7.bin, y9.bin, y7.bin, header.bin,
banner.bin, overlay/overlay_XXXX.bin, data/<Dateisystem>.
"""
import sys
from pathlib import Path
import ndspy.rom

ROOT = Path(__file__).resolve().parents[2]


def main(argv):
    rom_path = Path(argv[1]) if len(argv) > 1 else ROOT / "rom" / "Bleach3rdPhantom.nds"
    out = Path(argv[2]) if len(argv) > 2 else ROOT / "unpacked"
    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    (out / "overlay").mkdir(parents=True, exist_ok=True)
    raw = rom_path.read_bytes()
    (out / "header.bin").write_bytes(raw[:0x200])
    (out / "arm9.bin").write_bytes(rom.arm9)
    (out / "arm7.bin").write_bytes(rom.arm7)
    (out / "y9.bin").write_bytes(rom.arm9OverlayTable)
    (out / "y7.bin").write_bytes(rom.arm7OverlayTable)
    (out / "banner.bin").write_bytes(rom.iconBanner)
    for i, o in rom.loadArm9Overlays().items():
        (out / "overlay" / f"overlay_{i:04d}.bin").write_bytes(o.data)
    n = 0
    for fid, data in enumerate(rom.files):
        name = rom.filenames.filenameOf(fid)
        if name is None:
            continue
        p = out / "data" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        n += 1
    print(f"{rom.name.decode()} ({rom.idCode.decode()}): arm9 {len(rom.arm9)} B, "
          f"{len(rom.loadArm9Overlays())} Overlays, {n} Dateien → {out}")


if __name__ == "__main__":
    main(sys.argv)
