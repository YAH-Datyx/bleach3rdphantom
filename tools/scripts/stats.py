#!/usr/bin/env python3
"""Lesen + Patchen der Charakter-Stat-Tabelle in unpacked/arm9.bin.

Aufruf:
  python3 tools/scripts/stats.py list                # alle aktiven Chars zeigen
  python3 tools/scripts/stats.py show <id>           # einen Char im Detail
  python3 tools/scripts/stats.py set <id> hp=9999 atk=99 def=99 ...
                                                     # Felder ändern (in-place)
Felder: hp, mp, atk, def, spd, mag, level
"""
from __future__ import annotations
import struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARM9 = ROOT / "unpacked" / "arm9.bin"

TABLE_OFFSET = 0xfd882
ENTRY_SIZE   = 0x46
ENTRY_COUNT  = 255

FIELDS = {
    # name: (offset_in_struct, struct_format, max_value)
    "id":      (0x00, "<H", 0xFFFF),
    "sprite":  (0x02, "<H", 0xFFFF),
    "flag1":   (0x04, "<B", 0xFF),
    "flag2":   (0x05, "<B", 0xFF),
    "type":    (0x06, "<B", 0xFF),
    "level":   (0x07, "<B", 0xFF),
    "hp":      (0x08, "<H", 0xFFFF),
    "mp":      (0x0A, "<H", 0xFFFF),
    "atk":     (0x0C, "<B", 0xFF),
    "def":     (0x0D, "<B", 0xFF),
    "spd":     (0x0E, "<B", 0xFF),
    "mag":     (0x0F, "<B", 0xFF),
}

def read_entry(data: bytes, char_id: int) -> dict:
    off = TABLE_OFFSET + (char_id - 1) * ENTRY_SIZE
    out = {"_offset": off}
    for name, (sub, fmt, _) in FIELDS.items():
        (val,) = struct.unpack_from(fmt, data, off + sub)
        out[name] = val
    return out

def write_entry(data: bytearray, char_id: int, changes: dict) -> None:
    off = TABLE_OFFSET + (char_id - 1) * ENTRY_SIZE
    for name, value in changes.items():
        if name not in FIELDS:
            raise SystemExit(f"Unbekanntes Feld: {name}. Bekannt: {', '.join(FIELDS)}")
        sub, fmt, maxv = FIELDS[name]
        if not (0 <= value <= maxv):
            raise SystemExit(f"{name}={value} außerhalb [0..{maxv}]")
        struct.pack_into(fmt, data, off + sub, value)

def cmd_list(data: bytes) -> None:
    print(f"{'ID':>4} {'Lvl':>4} {'HP':>5} {'MP':>4} {'ATK':>4} {'DEF':>4} {'SPD':>4} {'MAG':>4}")
    for i in range(1, ENTRY_COUNT + 1):
        e = read_entry(data, i)
        if e["flag1"] == 0:  # Platzhalter überspringen
            continue
        print(f"{e['id']:>4} {e['level']:>4} {e['hp']:>5} {e['mp']:>4} "
              f"{e['atk']:>4} {e['def']:>4} {e['spd']:>4} {e['mag']:>4}")

def cmd_show(data: bytes, char_id: int) -> None:
    e = read_entry(data, char_id)
    print(f"Eintrag #{char_id} @ 0x{e['_offset']:x}")
    for name in FIELDS:
        print(f"  {name:8s} = {e[name]}")

def cmd_set(data: bytearray, char_id: int, kvs: list[str]) -> None:
    changes = {}
    for kv in kvs:
        if "=" not in kv:
            raise SystemExit(f"Ungültig: {kv} (erwartet key=wert)")
        k, v = kv.split("=", 1)
        changes[k.lower()] = int(v, 0)
    before = read_entry(bytes(data), char_id)
    write_entry(data, char_id, changes)
    after = read_entry(bytes(data), char_id)
    ARM9.write_bytes(data)
    print(f"Eintrag #{char_id} aktualisiert:")
    for k in changes:
        print(f"  {k}: {before[k]} → {after[k]}")
    print(f"Geschrieben: {ARM9}")

def main(argv: list[str]) -> int:
    if not ARM9.exists():
        print(f"Fehlt: {ARM9}", file=sys.stderr); return 1
    if len(argv) < 2 or argv[1] not in ("list", "show", "set"):
        print(__doc__); return 1
    data = bytearray(ARM9.read_bytes())
    if argv[1] == "list":
        cmd_list(bytes(data))
    elif argv[1] == "show":
        if len(argv) < 3: print("ID fehlt"); return 1
        cmd_show(bytes(data), int(argv[2]))
    elif argv[1] == "set":
        if len(argv) < 4: print("Aufruf: set <id> key=wert ..."); return 1
        cmd_set(data, int(argv[2]), argv[3:])
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
