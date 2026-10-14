"""Traegt die Vanilla-Pflicht-Faehigkeiten (370/401) in dumps/vanilla_ref.json ein.

Quelle ist dumps/characters.csv - ein Dump der UNMODIFIZIERTEN ROM (Kenpachi
dort noch mit lv 20 / atk 37 / abil "242 370 401"). Gebraucht wird nur die
Information, WELCHE Einheit 370 bzw. 401 im Original getragen hat; die
Slot-Position spielt keine Rolle, weil der Editor die Faehigkeiten ohnehin
hinten in die Slots 1-9 schreibt.

Einmalig laufen lassen (idempotent):
    python tools/gen_essential_abil.py
"""
import csv
import io
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(HERE, 'dumps', 'characters.csv')
VREF_PATH = os.path.join(HERE, 'dumps', 'vanilla_ref.json')

# kind=4 / Wert 999 in db_ability.inc - jeder Vanilla-Kampfchar traegt sie.
ESSENTIAL = (370, 401)


def main():
    rows = list(csv.DictReader(io.open(CSV_PATH, encoding='utf-8-sig')))
    ess = {}
    for r in rows:
        ids = [int(x) for x in r['ability_ids'].split() if x.isdigit()]
        have = [a for a in ESSENTIAL if a in ids]
        if have:
            ess[r['unit_id']] = have

    vref = json.load(open(VREF_PATH))
    vref['essential_abil'] = ess
    with open(VREF_PATH, 'w') as fh:
        json.dump(vref, fh, separators=(',', ':'))

    n370 = sum(1 for v in ess.values() if 370 in v)
    n401 = sum(1 for v in ess.values() if 401 in v)
    print(f'{len(ess)} Einheiten mit Pflicht-Faehigkeiten '
          f'(370: {n370}, 401: {n401}) -> {VREF_PATH}')


if __name__ == '__main__':
    main()
