#!/usr/bin/env python3
"""Scannt unpacked/data/ und klassifiziert Dateien anhand Magic-Bytes / Heuristiken.

Schreibt docs/inventory.md mit einer Tabelle: Pfad, Größe, vermuteter Typ, Magic.
Damit haben wir einen Startpunkt, um interessante Container zu identifizieren.
"""
from __future__ import annotations
import os, sys, struct
from pathlib import Path
from tabulate import tabulate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "unpacked" / "data"
OUT  = ROOT / "docs" / "inventory.md"

MAGIC = {
    b"NARC": "NARC archive (Nitro)",
    b"CARC": "CARC archive (komprimiertes NARC)",
    b"RGCN": "NCGR tile graphics",
    b"RLCN": "NCLR palette",
    b"RCSN": "NSCR tilemap",
    b"RECN": "NCER cell",
    b"RNAN": "NANR animation",
    b"RTFN": "NFTR font",
    b"SDAT": "SDAT sound archive",
    b"SSEQ": "SSEQ sequence",
    b"SBNK": "SBNK soundbank",
    b"SWAR": "SWAR wave archive",
    b"BMD0": "NSBMD 3D model",
    b"BTX0": "NSBTX 3D texture",
}

def classify(path: Path) -> tuple[str, str]:
    with path.open("rb") as f:
        head = f.read(4)
    if head in MAGIC:
        return MAGIC[head], head.decode("ascii", "replace")
    # LZ77/Huff/RLE (Nintendo compression marker im ersten Byte)
    if head and head[0] in (0x10, 0x11, 0x24, 0x28, 0x30):
        return f"Nintendo compressed (0x{head[0]:02X})", f"{head[0]:02X}"
    return "unknown", head.hex()

def main() -> int:
    if not DATA.exists():
        print(f"Erst entpacken: {DATA} fehlt. Führe tools/unpack.sh aus.", file=sys.stderr)
        return 1
    rows = []
    for p in sorted(DATA.rglob("*")):
        if p.is_file():
            kind, magic = classify(p)
            rows.append((str(p.relative_to(DATA)), p.stat().st_size, kind, magic))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        f.write("# ROM-Filesystem Inventar\n\n")
        f.write(f"Quelle: `unpacked/data/` — {len(rows)} Dateien\n\n")
        f.write(tabulate(rows, headers=["Pfad", "Größe", "Typ", "Magic"], tablefmt="github"))
        f.write("\n")
    print(f"Geschrieben: {OUT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
