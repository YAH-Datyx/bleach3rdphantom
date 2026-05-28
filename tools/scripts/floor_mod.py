#!/usr/bin/env python3
"""Floor-Modding-Helper für Bleach 3rd Phantom Tower-of-Souls.

Funktionen:
- Floor-Daten von einem Floor zum anderen kopieren
- Char-IDs auf einem Floor randomisieren (mit konfigurierbarem Pool)
- Stat-Buff (×N) für eine Liste von Char-IDs in arm9-Stat-Tabelle
- Tower-Tabelle Floor->Map-Mapping ändern

Siehe `docs/floor-roster.md` und `docs/char-ids.md` für Format-Details.
"""
from __future__ import annotations
import argparse, struct, shutil, random
from pathlib import Path
import ndspy.narc

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "unpacked" / "data" / "yamada" / "DataBase"
ARM9 = ROOT / "unpacked" / "arm9.bin"

DPOS_ENTRY = 54
PARTY_ENTRY = 14
TOWER_TABLE_OFFSET = 0xf3b58
STAT_TABLE_OFFSET = 0xfd882
STAT_ENTRY_SIZE = 0x46

# Bestätigte sichere Chars (siehe docs/char-ids.md)
SAFE_POOL = [
    21, 23, 25, 27, 29,                # Squad 11 (Vorsicht: NUR Enemy falls nicht Partner!)
    128, 130, 131, 134, 135, 136, 137, 138, 139, 140, 142, 143,  # gebufft, vermutlich Bleach-Chars
    216, 217, 218,                     # Floor 14 Original-Bosse (Ikkaku etc.)
    240, 245, 250, 254,                # Shiyo, Kon, Drunk Reaper, Ichigo
]

# Bekannte Crash-Chars (siehe docs/char-ids.md)
BROKEN_IDS = {100, 145, 146, 147, 150, 175, 195}


def dpos_path(floor: int) -> Path:
    return DATABASE / f"db_dpos_9{floor:02d}.narc"


def party_path(floor: int) -> Path:
    return DATABASE / f"db_party_9{floor:02d}.narc"


def list_floor(floor: int) -> None:
    """Liste alle Slots (Gegner + Partner) eines Floors."""
    print(f"=== Floor {floor} ===")
    # Partner
    party = ndspy.narc.NARC.fromFile(str(party_path(floor)))
    f = party.files[0]
    print(f"\nPartner ({party_path(floor).name}):")
    pos = 4
    while pos + 12 <= len(f):
        e = struct.unpack_from('<6H', f, pos)
        if e[0] == 10:
            print(f"  char_id={e[2]:3d}, level={e[1]:3d}, slot={e[5]}")
        pos += PARTY_ENTRY

    # Enemies
    dpos = ndspy.narc.NARC.fromFile(str(dpos_path(floor)))
    f0 = dpos.files[0]
    print(f"\nGegner ({dpos_path(floor).name}):")
    for i in range(len(f0) // DPOS_ENTRY):
        off = i * DPOS_ENTRY
        cid = struct.unpack_from('<H', f0, off+2)[0]
        if cid == 0:
            continue
        lvl = struct.unpack_from('<H', f0, off+4)[0]
        ai = struct.unpack_from('<H', f0, off+6)[0]
        x = struct.unpack_from('<H', f0, off+8)[0]
        y = struct.unpack_from('<H', f0, off+10)[0]
        team = struct.unpack_from('<H', f0, off+14)[0]
        print(f"  Slot {i:3d}: char={cid:3d} lvl={lvl:3d} ai={ai} pos=({x},{y}) team={team}")


def copy_floor(src: int, dst: int, also_map: bool = True) -> None:
    """Kopiert src's NARC-Dateien zu dst und optional die Map-ID in der Tower-Tabelle."""
    shutil.copy(dpos_path(src), dpos_path(dst))
    shutil.copy(party_path(src), party_path(dst))
    print(f"Floor {src} → Floor {dst}: NARC-Dateien kopiert")

    if also_map:
        # Map-ID auch übernehmen
        with open(ARM9, 'rb') as f:
            data = bytearray(f.read())
        src_map = struct.unpack_from('<H', data, TOWER_TABLE_OFFSET + (src-1)*6 + 2)[0]
        struct.pack_into('<H', data, TOWER_TABLE_OFFSET + (dst-1)*6 + 2, src_map)
        with open(ARM9, 'wb') as f:
            f.write(bytes(data))
        print(f"Tower-Map: Floor {dst}.map_id ← {src_map} (von Floor {src})")


def randomize_floor(floor: int, pool: list[int], level_range: tuple[int, int] = (60, 90),
                    exclude_partners: bool = True, seed: int | None = None) -> None:
    """Weist allen belegten Enemy-Slots zufällige Chars aus dem Pool zu."""
    if seed is not None:
        random.seed(seed)

    # Falls exclude_partners: hol die Partner-Char-IDs und entferne sie aus dem Pool
    final_pool = list(pool)
    if exclude_partners:
        party = ndspy.narc.NARC.fromFile(str(party_path(floor)))
        f = party.files[0]
        partner_ids = set()
        pos = 4
        while pos + 12 <= len(f):
            e = struct.unpack_from('<6H', f, pos)
            if e[0] == 10:
                partner_ids.add(e[2])
            pos += PARTY_ENTRY
        final_pool = [c for c in final_pool if c not in partner_ids]
        print(f"Partner-IDs ausgeschlossen: {sorted(partner_ids)}")

    final_pool = [c for c in final_pool if c not in BROKEN_IDS]
    if not final_pool:
        raise SystemExit("Pool leer nach Filterung!")

    random.shuffle(final_pool)
    pool_iter = iter(final_pool)

    narc = ndspy.narc.NARC.fromFile(str(dpos_path(floor)))
    f0 = bytearray(narc.files[0])

    print(f"\nRandomisiere Floor {floor} mit Pool {sorted(final_pool)}:")
    for i in range(len(f0) // DPOS_ENTRY):
        off = i * DPOS_ENTRY
        old_id = struct.unpack_from('<H', f0, off+2)[0]
        if old_id == 0:
            continue
        new_id = next(pool_iter, None)
        if new_id is None:
            random.shuffle(final_pool)
            pool_iter = iter(final_pool)
            new_id = next(pool_iter)
        new_lvl = random.randint(*level_range)
        struct.pack_into('<H', f0, off+2, new_id)
        struct.pack_into('<H', f0, off+4, new_lvl)
        print(f"  Slot {i:3d}: {old_id:3d} → {new_id:3d}, lvl={new_lvl}")

    narc.files[0] = bytes(f0)
    narc.saveToFile(str(dpos_path(floor)))


def buff_chars(char_ids: list[int], factor: float) -> None:
    """Multipliziert HP/MP/ATK/DEF/SPD/MAG einer Char-Liste in arm9 Stat-Tabelle."""
    with open(ARM9, 'rb') as f:
        data = bytearray(f.read())

    for cid in char_ids:
        off = STAT_TABLE_OFFSET + (cid-1) * STAT_ENTRY_SIZE
        if data[off+4] == 0:  # flag1=0 → inaktiv
            print(f"  ID {cid}: inaktiv, übersprungen")
            continue
        hp = struct.unpack_from('<H', data, off+8)[0]
        mp = struct.unpack_from('<H', data, off+0xA)[0]
        atk, dfn, spd, mag = data[off+0xC], data[off+0xD], data[off+0xE], data[off+0xF]
        new = (
            min(int(hp*factor), 65535),
            min(int(mp*factor), 65535),
            min(int(atk*factor), 255),
            min(int(dfn*factor), 255),
            min(int(spd*factor), 255),
            min(int(mag*factor), 255),
        )
        struct.pack_into('<H', data, off+8, new[0])
        struct.pack_into('<H', data, off+0xA, new[1])
        data[off+0xC] = new[2]
        data[off+0xD] = new[3]
        data[off+0xE] = new[4]
        data[off+0xF] = new[5]
        print(f"  ID {cid:3d}: HP {hp}→{new[0]}, ATK {atk}→{new[2]}, DEF {dfn}→{new[3]}, SPD {spd}→{new[4]}, MAG {mag}→{new[5]}")

    with open(ARM9, 'wb') as f:
        f.write(bytes(data))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    sp = sub.add_parser('list', help='Liste alle Slots eines Floors')
    sp.add_argument('floor', type=int)

    sp = sub.add_parser('copy', help='Kopiere einen Floor auf einen anderen')
    sp.add_argument('src', type=int)
    sp.add_argument('dst', type=int)
    sp.add_argument('--no-map', action='store_true', help='Nicht die Map-ID übernehmen')

    sp = sub.add_parser('randomize', help='Randomisiere alle Enemy-Slots eines Floors')
    sp.add_argument('floor', type=int)
    sp.add_argument('--min-lvl', type=int, default=60)
    sp.add_argument('--max-lvl', type=int, default=90)
    sp.add_argument('--seed', type=int)

    sp = sub.add_parser('buff', help='Buff HP/ATK/DEF/SPD/MAG einer Char-Liste')
    sp.add_argument('--factor', type=float, default=2.0)
    sp.add_argument('ids', nargs='+', type=int)

    args = p.parse_args()
    if args.cmd == 'list':
        list_floor(args.floor)
    elif args.cmd == 'copy':
        copy_floor(args.src, args.dst, also_map=not args.no_map)
    elif args.cmd == 'randomize':
        randomize_floor(args.floor, SAFE_POOL, (args.min_lvl, args.max_lvl), seed=args.seed)
    elif args.cmd == 'buff':
        buff_chars(args.ids, args.factor)


if __name__ == '__main__':
    main()
