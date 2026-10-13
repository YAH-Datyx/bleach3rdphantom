"""Spielstand-Analyse (.dsv Battery-Saves) fuer den Save-Editor.

Erkannte Struktur (2026-07-08):
  - .dsv = 64 KB SRAM + 122-B-DeSmuME-Footer
  - Spielername (UTF-16LE) bei ~0x1018 / 0x401c / 0x7020
  - 3 Datenbloecke a ~0x2900: 0x1000, 0x4000, 0x7000 (Slot 1, Slot 2,
    zuletzt-genutzt-Kopie?) + Block 0xa000 (System?)
  - Charakter-Records: Stride 156 Bytes (Autokorrelations-Peak) -
    Feld-Layout noch NICHT geknackt -> Kalibrier-Diffs noetig!

CLI:
  python tools/saveedit.py diff alt.dsv neu.dsv   # geaenderte Bereiche
"""
import sys

SRAM = 65536
BLOCKS = [(0x1000, 0x3900, 'Slot A'), (0x4000, 0x6900, 'Slot B'),
          (0x7000, 0x9900, 'Slot C'), (0xa000, 0xc200, 'System')]
STRIDE = 156


def load(path):
    d = open(path, 'rb').read()
    return d[:SRAM]


def diff(a_path, b_path, ctx=8):
    a, b = load(a_path), load(b_path)
    runs = []
    i = 0
    while i < SRAM:
        if a[i] != b[i]:
            j = i
            while j < SRAM and (a[j] != b[j] or
                                (j + 4 < SRAM and a[j:j+4] != b[j:j+4])):
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    print(f'{len(runs)} geaenderte Bereiche:')
    for s, e in runs:
        blk = next((n for x, y, n in BLOCKS if x <= s < y), '?')
        rec = (s - 0x1000) // STRIDE if blk == 'Slot A' else None
        rel = (s - 0x1000) % STRIDE if blk == 'Slot A' else None
        tag = f'  [{blk}' + (f', Record ~{rec} Feld +{rel}' if rec is not None else '') + ']'
        print(f'  0x{s:04X}..0x{e:04X} ({e-s:3d} B){tag}')
        print(f'    alt: {a[max(0,s-ctx):e+ctx].hex(" ")}')
        print(f'    neu: {b[max(0,s-ctx):e+ctx].hex(" ")}')
    return runs


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'diff':
        diff(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
