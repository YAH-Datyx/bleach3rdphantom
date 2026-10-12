#!/usr/bin/env python3
"""Schreibt Änderungen aus unpacked-decomp/data zurück nach unpacked/data.

Für jede Huffman-komprimierte Datei in unpacked/data wird verglichen: Weicht
die entpackte Fassung in unpacked-decomp/ ab, wird sie mit demselben Modus
(4/8 Bit) neu komprimiert und ersetzt das Original. Unkomprimierte Dateien
werden 1:1 übernommen, wenn sie sich unterscheiden.

  python3 tools/scripts/recompress.py [--dry-run]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compress import compress_huffman      # noqa: E402
from decompress import decompress_huffman  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "unpacked" / "data"
DEC = ROOT / "unpacked-decomp" / "data"


def recompress(src: Path = SRC, dec: Path = DEC, dry_run: bool = False) -> list[str]:
    changed = []
    for d in sorted(dec.rglob("*")):
        if not d.is_file():
            continue
        s = src / d.relative_to(dec)
        if not s.exists():
            continue  # neue Dateien müssen bewusst ins Dateisystem (siehe build_rom.py)
        orig, edited = s.read_bytes(), d.read_bytes()
        if orig[:1] in (b"\x24", b"\x28") and len(orig) > 4:
            if decompress_huffman(orig) == edited:
                continue
            new = compress_huffman(edited, orig[0] & 0x0F)
        elif orig != edited:
            new = edited
        else:
            continue
        changed.append(str(s.relative_to(src)))
        if not dry_run:
            s.write_bytes(new)
    return changed


if __name__ == "__main__":
    ch = recompress(dry_run="--dry-run" in sys.argv)
    for c in ch:
        print("geändert:", c)
    print(f"{len(ch)} Datei(en){' (dry-run)' if '--dry-run' in sys.argv else ''}")
