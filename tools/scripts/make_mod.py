#!/usr/bin/env python3
"""Ein Befehl: Mods anwenden → gepatchte ROM + xdelta-Patch bauen.

  python3 tools/scripts/make_mod.py mods/fix-partner-conflicts.json [weitere mods ...]
      [--base rom/Bleach3rdPhantom.nds] [--out build/Bleach3rdPhantom.mod.nds]
      [--assets unpacked-decomp/data]   # optional: geänderte Grafiken/Animationen mitnehmen

Ablauf:
  1. Basis-ROM in einen frischen Arbeitsordner entpacken (build/work/), damit
     wiederholte Läufe die Mods nicht doppelt anwenden
  2. Daten-Mods (JSON, siehe docs/gamedata-format.md) anwenden + validieren
  3. optional geänderte Assets aus --assets neu komprimieren und übernehmen
  4. ROM bauen + xdelta-Patch gegen die Basis-ROM (falls xdelta3 installiert ist)
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_rom   # noqa: E402
import gamedata    # noqa: E402
import recompress  # noqa: E402


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mods", nargs="*", type=Path)
    p.add_argument("--base", type=Path, default=ROOT / "rom" / "Bleach3rdPhantom.nds")
    p.add_argument("--out", type=Path, default=ROOT / "build" / "Bleach3rdPhantom.mod.nds")
    p.add_argument("--assets", type=Path, help="entpackte Assets mit Änderungen (z. B. unpacked-decomp/data)")
    a = p.parse_args(argv)

    work = ROOT / "build" / "work"
    shutil.rmtree(work, ignore_errors=True)
    subprocess.run([sys.executable, str(HERE / "unpack_rom.py"), str(a.base), str(work)], check=True)

    data, owners, log = gamedata.load_rom_data(work), {}, []
    for m in a.mods:
        gamedata.apply_mod(data, json.loads(m.read_text()), owners, log)
        print(f"Mod angewendet: {m}")
    for line in log:
        print(line)
    for line in gamedata.validate(data):
        print("WARNUNG:", line)
    gamedata.save_rom_data(work, data)

    if a.assets:
        ch = recompress.recompress(work / "data", a.assets)
        print(f"{len(ch)} Asset-Datei(en) übernommen")

    changed = build_rom.build(a.base, a.out, work)
    print(f"{len(changed)} geänderte Datei(en) in der ROM")
    print(f"ROM:   {a.out}  (sha1 {sha1(a.out)})")
    patch = a.out.with_suffix(".xdelta")
    if shutil.which("xdelta3"):
        subprocess.run(["xdelta3", "-e", "-9", "-f", "-s", str(a.base), str(a.out), str(patch)], check=True)
        print(f"Patch: {patch}  ({patch.stat().st_size // 1024} KB, Basis-sha1 {sha1(a.base)})")
    else:
        print("xdelta3 nicht installiert — nur ROM gebaut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
