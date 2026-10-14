"""Setzt das dpos-Feld unk3 (= ai_mode, +0x06) der Kampagnen-Etagen zurueck.

HINTERGRUND (HANDOVER Abschnitt 7.1 / Aufgabe 2)
Auf den Etagen 11-15 wurde unk3 pauschal auf 15 gesetzt - auf Basis einer
inzwischen WIDERLEGTEN HP-Theorie. Vanilla nutzt quer durch den Turm
0/10/13/15/17/18, Mehrheit 10. Die Ghidra-Analyse des US-Zweigs liest das
Feld als u8 "ai_mode" bei +0x06, das als Festkomma (<<12) an FUN_020A2688
geht; 10 = aktiv/boss, 15 = passiv/patrol. Wenn das stimmt, wurden die
Kampagnen-Gegner versehentlich PASSIVER gemacht.

Dieses Skript aendert ausschliesslich unk3 - Level, Position, Blickrichtung,
Charakter und raw bleiben, wie sie sind.

    python tools/fix_unk3.py                  # nur anzeigen (Trockenlauf)
    python tools/fix_unk3.py --write          # Vanilla-Wert je Slot schreiben
    python tools/fix_unk3.py --mode aktiv --write      # alles auf 10
    python tools/fix_unk3.py --floors 11,12 --write

Modi:
  vanilla (Standard)  Wert des GLEICHEN Slots aus dumps/tower_floors.json
                      (Dump der unmodifizierten ROM). Kein Rateschritt.
                      Slots, die es im Original nicht gab (Extra-Slots des
                      Randomizers), bekommen den haeufigsten Wert der Etage.
  aktiv               alles auf 10 - die Wette auf "10 = aktiv/boss".
                      Das ist der eigentliche Test der ai_mode-Hypothese.

VORHER EIN BACKUP DER ROM ANLEGEN. Das Skript schreibt in die Arbeits-ROM.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from romfs import RomFS, DEFAULT_ROM          # noqa: E402
from tower import floor_units, pack_units     # noqa: E402

VANILLA_FLOORS = os.path.join(ROOT, 'dumps', 'tower_floors.json')


def vanilla_unk3(floor):
    """-> ({slot: unk3}, fallback) aus dem Vanilla-Dump."""
    data = json.load(open(VANILLA_FLOORS))
    units = data.get(str(floor), {}).get('units', [])
    by_slot = {u['slot']: u['unk3'] for u in units}
    common = collections.Counter(by_slot.values()).most_common(1)
    return by_slot, (common[0][0] if common else 10)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--rom', default=DEFAULT_ROM)
    ap.add_argument('--floors', default='11,12,13,14,15')
    ap.add_argument('--mode', choices=('vanilla', 'aktiv'), default='vanilla')
    ap.add_argument('--write', action='store_true',
                    help='wirklich in die ROM schreiben (sonst Trockenlauf)')
    a = ap.parse_args()

    floors = [int(x) for x in a.floors.replace(' ', '').split(',') if x]
    fs = RomFS(a.rom)
    print(f'ROM:   {a.rom}')
    print(f'Modus: {a.mode}   Etagen: {floors}'
          f'   {"SCHREIBEN" if a.write else "Trockenlauf"}\n')

    total = 0
    for floor in floors:
        units = floor_units(fs, floor)
        by_slot, fallback = vanilla_unk3(floor)
        changes = []
        for u in units:
            if a.mode == 'aktiv':
                new = 10
            else:
                new = by_slot.get(u['slot'], fallback)
            if new != u['unk3']:
                changes.append((u['slot'], u['char'], u['unk3'], new))
                u['unk3'] = new
        print(f'Etage {floor:>2}: {len(units):>2} Einheiten, '
              f'{len(changes):>2} Aenderungen')
        for slot, char, old, new in changes:
            extra = '' if slot in by_slot else '  (Extra-Slot -> Etagen-Mehrheit)'
            print(f'    Slot {slot:>3}  Char {char:>3}:  {old:>2} -> {new:>2}{extra}')
        if changes and a.write:
            # pack_units liefert nur die neuen NARC-Bytes - schreiben muss fs
            fs.write(f'/yamada/DataBase/db_dpos_{900 + floor}.narc',
                     pack_units(fs, floor, units))
        total += len(changes)

    print(f'\n{total} Records betroffen.')
    if a.write:
        print('In die ROM geschrieben. Jetzt in DeSmuME testen: greifen die '
              'Gegner der Etagen 11-15 jetzt aktiver an?')
    else:
        print('Trockenlauf - nichts geschrieben. Mit --write anwenden.')


if __name__ == '__main__':
    main()
