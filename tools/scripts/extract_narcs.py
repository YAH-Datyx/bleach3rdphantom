#!/usr/bin/env python3
"""Geht rekursiv durch unpacked-decomp/data/, extrahiert jede NARC-Datei
in einen gleichnamigen Ordner mit Suffix .extracted/ daneben.
Sub-Dateien behalten ihre internen Namen (falls FNT vorhanden), sonst 0000.bin, 0001.bin, ...
"""
from __future__ import annotations
import sys
from pathlib import Path
import ndspy.narc

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "unpacked-decomp" / "data"

def extract(narc_path: Path) -> int:
    try:
        narc = ndspy.narc.NARC.fromFile(str(narc_path))
    except Exception as e:
        print(f"  Fehler {narc_path.name}: {e}")
        return 0
    out_dir = narc_path.with_suffix(narc_path.suffix + ".extracted")
    out_dir.mkdir(exist_ok=True)
    count = 0
    # ndspy: narc.filenames ist ein Folder-Objekt; flat-Liste über folder
    try:
        flat = list(narc.filenames.folders) if narc.filenames else []
    except Exception:
        flat = []
    # Einfacher Weg: Index-basiert dumpen, Namen via filenames-Tree wenn möglich
    for i, file_bytes in enumerate(narc.files):
        name = None
        try:
            name = narc.filenames.filenameOfFileWithID(i) if narc.filenames else None
        except Exception:
            name = None
        if not name:
            name = f"{i:04d}.bin"
        # Pfad-Trennung
        out_path = out_dir / name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(file_bytes)
        count += 1
    return count

def main() -> int:
    if not SRC.exists():
        print(f"Erst tools/scripts/decompress.py ausführen — {SRC} fehlt", file=sys.stderr)
        return 1
    n_narcs = n_files = 0
    for p in SRC.rglob("*"):
        if not p.is_file(): continue
        with p.open("rb") as f:
            magic = f.read(4)
        if magic != b"NARC": continue
        c = extract(p)
        if c > 0:
            n_narcs += 1
            n_files += c
            print(f"  {p.relative_to(SRC)} → {c} Dateien")
    print(f"\nNARCs extrahiert: {n_narcs}")
    print(f"Total Sub-Dateien: {n_files}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
