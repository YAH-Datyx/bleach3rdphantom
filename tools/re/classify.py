#!/usr/bin/env python3
"""Klassifiziert alle Dateien in unpacked/data nach Format (Magic, Kompression,
NARC-Inhalt) und gruppiert sie nach Verzeichnis + Namensmuster.

  python3 tools/re/classify.py [--md docs/file-formats-scan.md]
"""
import argparse, collections, re, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "unpacked" / "data"

MAGIC = {
    b"NARC": "NARC", b"RGCN": "NCGR", b"RLCN": "NCLR", b"RCSN": "NSCR", b"RECN": "NCER",
    b"RNAN": "NANR", b"RTFN": "NFTR", b"SDAT": "SDAT", b"BMD0": "NSBMD", b"BTX0": "NSBTX",
    b"BCA0": "NSBCA", b"BTP0": "NSBTP", b"BTA0": "NSBTA", b"BMA0": "NSBMA", b"CPK ": "CPK",
    b"RCMN": "NMCR", b"RECM": "NMAR", b"BMG": "BMG",
}


def kind(b: bytes) -> str:
    if len(b) < 4:
        return "tiny"
    for m, k in MAGIC.items():
        if b.startswith(m):
            return k
    if b[:2] == b"\x80\x00":
        return "ADX"
    if b[:4] == b"\x40\x55\x54\x46":
        return "@UTF"
    if b[0] in (0x10, 0x11) and 0 < int.from_bytes(b[1:4], "little") < 16 << 20:
        return f"LZ{b[0]:x}?"
    if b[0] in (0x24, 0x28) and 0 < int.from_bytes(b[1:4], "little") < 16 << 20:
        return "HUFF?"
    if all(32 <= c < 127 or c in (9, 10, 13) for c in b[:64]):
        return "text"
    return "raw"


def narc_content(b: bytes) -> str:
    try:
        import ndspy.narc
        n = ndspy.narc.NARC(b)
    except Exception:
        return "?"
    kinds = collections.Counter(kind(f) for f in n.files)
    return f"{len(n.files)} files: " + ", ".join(f"{k}×{v}" for k, v in kinds.most_common(4))


def pattern(rel: str) -> str:
    return re.sub(r"\d+", "#", rel)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--md", type=Path)
    a = p.parse_args()
    groups = collections.defaultdict(lambda: {"n": 0, "size": 0, "kinds": collections.Counter(), "narc": ""})
    for f in sorted(DATA.rglob("*")):
        if not f.is_file():
            continue
        b = f.read_bytes()
        g = groups[pattern(str(f.relative_to(DATA)))]
        g["n"] += 1
        g["size"] += len(b)
        k = kind(b)
        g["kinds"][k] += 1
        if k == "NARC" and not g["narc"]:
            g["narc"] = narc_content(b)
    rows = sorted(groups.items(), key=lambda kv: -kv[1]["size"])
    lines = ["| Muster | Anzahl | Größe | Format | NARC-Inhalt (Beispiel) |", "|---|---|---|---|---|"]
    for pat, g in rows:
        ks = ", ".join(f"{k}×{v}" if v > 1 else k for k, v in g["kinds"].most_common(3))
        lines.append(f"| `{pat}` | {g['n']} | {g['size'] // 1024} KB | {ks} | {g['narc']} |")
    out = "\n".join(lines)
    total = collections.Counter()
    for g in groups.values():
        for k, v in g["kinds"].items():
            total[k] += v
    summary = "Gesamt: " + ", ".join(f"{k}×{v}" for k, v in total.most_common())
    if a.md:
        a.md.write_text(f"# Datei-Scan (automatisch)\n\n{summary}\n\n{out}\n")
    print(summary)
    print(out)


if __name__ == "__main__":
    main()
