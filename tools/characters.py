"""Charakterdaten auslisten: dumps/characters.csv + names.csv + abilities.csv.

Quellen:
  /yamada/ScrDat/s_name.bin           Namenstabelle (Index = Charakter-ID)
  /yamada/DataBase/db_status.inc      Basiswerte pro Einheit (Klartext-Tabelle)
  /yamada/DataBase/db_growt.inc       Wachstumsraten
  /yamada/DataBase/db_ability_name.bin Faehigkeitsnamen
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from romfs import RomFS
from formats import bgsm_strings, parse_inc

HERE = os.path.dirname(os.path.abspath(__file__))
DUMPS = os.path.join(HERE, '..', 'dumps')

# Spaltenbelegung db_status.inc (27 Felder pro Zeile, per Vergleich mit
# Spielverhalten geraten - unk* = noch nicht sicher identifiziert):
COLS = ['person', 'unit', 'playable', 'unk3', 'face', 'lv', 'hp', 'sp',
        'atk', 'def', 'spi', 'spd', 'mov', 'unk13', 'unk14', 'unk15',
        'unk16', 'unk17', 'unk18', 'equip[10]', 'unk20', 'abilities[10]',
        'unk22', 'unk23']


def main():
    fs = RomFS()
    os.makedirs(DUMPS, exist_ok=True)
    names = bgsm_strings(fs.read('/yamada/ScrDat/s_name.bin'))
    abil_names = bgsm_strings(fs.read('/yamada/DataBase/db_ability_name.bin'))
    status = parse_inc(fs.read('/yamada/DataBase/db_status.inc').decode('ascii'))

    with open(os.path.join(DUMPS, 'names.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['id', 'name'])
        for i, n in sorted(names.items()):
            w.writerow([i, n])

    with open(os.path.join(DUMPS, 'abilities.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['id', 'name'])
        for i, n in sorted(abil_names.items()):
            w.writerow([i, n])

    with open(os.path.join(DUMPS, 'characters.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['unit_id', 'name'] + COLS[2:19] + ['equipment', 'unk20',
                    'ability_ids', 'ability_names', 'unk22', 'unk23'])
        for row in status:
            unit = row[1]
            nm = names.get(unit, '?')
            flat = row[2:19]
            equip = row[19]
            unk20 = row[20]
            abil = [a for a in row[21] if a]
            abil_txt = ' / '.join(abil_names.get(a, f'?{a}') for a in abil[1:]) if len(abil) > 1 else ''
            w.writerow([unit, nm] + flat +
                       [' '.join(map(str, [e for e in equip if e])), unk20,
                        ' '.join(map(str, abil[1:])), abil_txt, row[22], row[23]])
    print(f"{len(status)} Einheiten -> dumps/characters.csv, {len(names)} Namen -> names.csv, "
          f"{len(abil_names)} Faehigkeiten -> abilities.csv")


if __name__ == '__main__':
    main()
