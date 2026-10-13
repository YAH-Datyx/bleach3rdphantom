"""Bleach Tower (Postgame-Turm, 30 Etagen) ansehen und bearbeiten.

Nutzung:
  python tower.py dump                 -> tower_dump.txt + tower_floors.json
  python tower.py build floors.json    -> schreibt geaenderte Etagen in die ROM

Datenquellen in der ROM:
  /yamada/DataBase/db_btower.inc    {Etage, MapNr, PartyIndex} x30
  /yamada/DataBase/db_dpos_9NN.narc Einheiten der Etage NN (Subfile 0),
                                    Records a 54 Bytes:
    u8  slot
    u8  team      (3 = Gegnerseite - ALLE Turm-Gegner, 1 = Spielerseite!
                   Feld heisst hier 'active'. 1 laesst Einheiten als
                   Player-Team spawnen.)
    u16 char      (Charakter-ID, Namen siehe names.csv)
    u16 level
    u16 unk3      (immer 10)
    u16 x, y      (Grid-Koordinaten)
    u16 dir       (Blickrichtung 0-3)
    u16 unk7      (immer 1)
    u16 raw[18]   (AI/Drops/Extras - unveraendert lassen)
  /yamada/DataBase/db_party_9NN.narc Spieler-Deployment-Slots
"""
import json, struct, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from romfs import RomFS
from formats import narc_subfiles, narc_replace_subfile, bgsm_strings, parse_inc

HERE = os.path.dirname(os.path.abspath(__file__))
REC = 54


def load_names(fs):
    return bgsm_strings(fs.read('/yamada/ScrDat/s_name.bin'))


def floor_units(fs, floor):
    data = fs.read(f'/yamada/DataBase/db_dpos_{900+floor}.narc')
    sub = narc_subfiles(data)[0]
    units = []
    for r in range(len(sub) // REC):
        rec = sub[r * REC:(r + 1) * REC]
        slot, active = rec[0], rec[1]
        f = struct.unpack('<26H', rec[2:])
        if not any(f):
            continue
        units.append({
            'slot': slot, 'active': active,
            'char': f[0], 'level': f[1], 'unk3': f[2],
            'x': f[3], 'y': f[4], 'dir': f[5], 'unk7': f[6],
            'raw': list(f[7:]),
        })
    return units


def pack_units(fs, floor, units, base=None):
    """base: optionaler NARC-Rohinhalt als Grundlage (z. B. Donor-Etage nach
    Map-Wechsel) - sonst wird die aktuelle dpos-NARC der Etage benutzt."""
    data = base if base is not None else fs.read(f'/yamada/DataBase/db_dpos_{900+floor}.narc')
    subs = narc_subfiles(data)
    sub = bytearray(subs[0])
    # Payloads aller Records leeren, Slot-/Aktiv-Bytes des Originals behalten
    # (leere Records haben je nach Slot aktiv=0 oder 1 - nicht anfassen)
    for r in range(len(sub) // REC):
        sub[r * REC + 2:(r + 1) * REC] = b'\0' * (REC - 2)
    for u in units:
        r = u['slot'] - 1
        rec = struct.pack('<BB26H', u['slot'], u.get('active', 1),
                          u['char'], u['level'], u.get('unk3', 10),
                          u['x'], u['y'], u.get('dir', 0), u.get('unk7', 1),
                          *u.get('raw', [0] * 19))
        sub[r * REC:(r + 1) * REC] = rec
    return narc_replace_subfile(data, 0, bytes(sub))


# ---------- Subfile 1 = AI-Skill-Scripts pro Einheit ----------
# Aufbau: 36-u16-Header + je Einheiten-Record ein 36-u16-Block (Slot-Reihenfolge).
# Block = u16 header((?<<8)|idx), dann u16[] Skill-/Ability-IDs, 0xFFFF/0-Padding.
AI_HDR = 36 * 2          # Byte-Offset des ersten Blocks
AI_BLK = 36 * 2          # Blockgroesse in Bytes (36 u16)


def ai_block_count(narc):
    subs = narc_subfiles(narc)
    if len(subs) < 2:
        return 0
    return (len(subs[1]) - AI_HDR) // AI_BLK


def ai_block(narc, idx):
    """Skill/Ability-IDs des Blocks idx (0-basiert) -> (header, [ids...])."""
    s1 = narc_subfiles(narc)[1]
    off = AI_HDR + idx * AI_BLK
    vals = struct.unpack_from('<36H', s1, off)
    ids = [v for v in vals[1:] if v not in (0, 0xFFFF)]
    return vals[0], ids


def set_ai_block(narc, idx, ids):
    """Block idx mit neuer ID-Liste ueberschreiben (Header bleibt, max 35 IDs,
    Rest mit 0xFFFF gepolstert). Gibt den neuen NARC zurueck."""
    subs = narc_subfiles(narc)
    s1 = bytearray(subs[1])
    off = AI_HDR + idx * AI_BLK
    hdr = struct.unpack_from('<H', s1, off)[0]
    ids = list(ids)[:35]
    block = [hdr] + ids + [0xFFFF] * (35 - len(ids))
    struct.pack_into('<36H', s1, off, *block)
    return narc_replace_subfile(narc, 1, bytes(s1))


def party_slots(fs, floor):
    """Spieler-Startpositionen einer Turm-Etage (db_party_9NN, Records a 14 B)."""
    data = fs.read(f'/yamada/DataBase/db_party_{900+floor}.narc')
    sub = narc_subfiles(data)[0]
    slots = []
    for i in range(len(sub) // 14):
        rid, unk, x, y, unk2, unk3 = struct.unpack_from('<IHHHHH', sub, i * 14)
        slots.append({'id': rid, 'unk': unk, 'x': x, 'y': y, 'unk2': unk2, 'unk3': unk3})
    return slots


def pack_party(fs, floor, slots):
    data = fs.read(f'/yamada/DataBase/db_party_{900+floor}.narc')
    subs = narc_subfiles(data)
    sub = bytearray(subs[0])
    assert len(slots) == len(sub) // 14, 'Slot-Anzahl muss gleich bleiben'
    for i, s in enumerate(slots):
        struct.pack_into('<IHHHHH', sub, i * 14, s['id'], s['unk'],
                         s['x'], s['y'], s['unk2'], s['unk3'])
    return narc_replace_subfile(data, 0, bytes(sub))


def cmd_dump(fs):
    names = load_names(fs)
    btower = parse_inc(fs.read('/yamada/DataBase/db_btower.inc').decode('ascii'))
    floors = {}
    lines = []
    for floor, mapno, party in [(r[0], r[1], r[2]) for r in btower]:
        units = floor_units(fs, floor)
        floors[floor] = {'map': mapno, 'party': party, 'units': units}
        lines.append(f"=== Etage {floor}  (Map {mapno}, Party {900+party}) ===")
        for u in units:
            nm = names.get(u['char'], f"?{u['char']}")
            lines.append(f"  slot {u['slot']:3d}: {nm:<16} LV{u['level']:<3} pos=({u['x']},{u['y']}) dir={u['dir']}")
        lines.append('')
    open(os.path.join(HERE, '..', 'dumps', 'tower_dump.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    json.dump(floors, open(os.path.join(HERE, '..', 'dumps', 'tower_floors.json'), 'w'), indent=1)
    print("dumps/tower_dump.txt und dumps/tower_floors.json geschrieben")


def cmd_build(fs, json_path, out_rom=None):
    floors = json.load(open(json_path))
    for floor_s, fl in floors.items():
        floor = int(floor_s)
        new_narc = pack_units(fs, floor, fl['units'])
        fs.write(f'/yamada/DataBase/db_dpos_{900+floor}.narc', new_narc, out_rom)
        print(f"Etage {floor}: db_dpos_{900+floor}.narc gepatcht")


if __name__ == '__main__':
    fs = RomFS()
    if sys.argv[1] == 'dump':
        cmd_dump(fs)
    elif sys.argv[1] == 'build':
        cmd_build(fs, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
