#!/usr/bin/env python3
"""Offenes Datenformat für Bleach: The 3rd Phantom.

Exportiert alle bisher reverse-engineerten Tabellen aus `unpacked/` nach JSON,
schreibt JSON verlustfrei zurück und wendet Mods (kleine JSON-Patches) in
Reihenfolge an — damit lassen sich eigene Inhalte ergänzen und mehrere Mods
(oder Daten aus anderen Projekten) zusammenführen.

Aufruf:
  python3 tools/scripts/gamedata.py export  [--out gamedata]
  python3 tools/scripts/gamedata.py import  [--src gamedata]
  python3 tools/scripts/gamedata.py apply   mods/a.json mods/b.json ... [--dry-run]
  python3 tools/scripts/gamedata.py validate

Unbekannte Bytes werden als Hex-String (`_raw`) mitgeführt, damit
export → import byte-identisch ist. Format-Details: docs/gamedata-format.md
"""
from __future__ import annotations
import argparse, json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNPACKED = ROOT / "unpacked"

STAT_TABLES = {
    # name: (offset in arm9.bin, max. Einträge); beide enden mit model == 0xFFFF.
    # Das früher notierte VS-Offset 0xffc56 lag mitten in der Story-Tabelle.
    "characters":    (0xfd882, 255),   # db_status.inc
    "characters_vs": (0x11a938, 37),   # db_VSstatus.inc, IDs nicht fortlaufend
}
STAT_ENTRY = 0x46
TOWER_OFFSET = 0xf3b58
TOWER_COUNT = 30
DPOS_ENTRY = 54
PARTY_HEADER = 4
PARTY_ENTRY = 14
FLOORS = range(1, TOWER_COUNT + 1)

BROKEN_IDS = {30, 90, 100, 110, 145, 146, 147, 150, 170, 175, 193, 195}

# name: (offset, struct-format) — alles andere bleibt in _raw erhalten
STAT_FIELDS = {
    "model": (0x00, "<H"), "id": (0x02, "<H"), "flag1": (0x04, "<B"),
    "flag2": (0x05, "<B"), "type": (0x06, "<B"), "level": (0x07, "<B"),
    "hp": (0x08, "<H"), "mp": (0x0A, "<H"), "atk": (0x0C, "<B"),
    "def": (0x0D, "<B"), "spd": (0x0E, "<B"), "mag": (0x0F, "<B"),
    "items": (0x1A, "<10H"), "skills": (0x30, "<10H"),
}
DPOS_FIELDS = {
    # instance_id = 2 Bytes: low = Eintrags-Index, high = Art (3 = Gegner, 5 = Sonder-Spawn)
    "instance_id": (0x00, "<H"), "char_id": (0x02, "<H"), "level": (0x04, "<H"),
    "ai_mode": (0x06, "<H"), "x": (0x08, "<H"), "y": (0x0A, "<H"),
    "team": (0x0E, "<H"),
    "wave": (0x10, "<h"),  # Spawn-Gruppe: Tower-Start spawnt nur 0 (docs/spawn-logic.md)
}
DPOS_MAX_READ = 64     # Spawn-Schleife liest nur die ersten 64 Einträge
ACTOR_SLOTS = 32       # alle Figuren zusammen; die Party belegt davon bis zu 8
PARTY_SLOTS = 8
PARTY_FIELDS = {
    "type": (0x00, "<H"), "level": (0x02, "<H"), "char_id": (0x04, "<H"),
    "slot": (0x0A, "<H"),
}


# --- generisches Struct-Mapping -------------------------------------------

def unpack_struct(raw: bytes, fields: dict) -> dict:
    out = {}
    for name, (off, fmt) in fields.items():
        vals = struct.unpack_from(fmt, raw, off)
        out[name] = list(vals) if len(vals) > 1 else vals[0]
    out["_raw"] = raw.hex()
    return out


def pack_struct(obj: dict, fields: dict, size: int) -> bytes:
    buf = bytearray(bytes.fromhex(obj["_raw"]) if "_raw" in obj else bytes(size))
    if len(buf) != size:
        raise ValueError(f"_raw hat {len(buf)} statt {size} Bytes")
    for name, (off, fmt) in fields.items():
        if name not in obj:
            continue
        val = obj[name]
        try:
            struct.pack_into(fmt, buf, off, *(val if isinstance(val, list) else [val]))
        except struct.error as e:
            raise ValueError(f"Feld {name}={val!r}: {e}") from None
    return bytes(buf)


# --- Lesen / Schreiben der ROM-Daten --------------------------------------

def dpos_path(unpacked: Path, floor: int) -> Path:
    return unpacked / "data" / "yamada" / "DataBase" / f"db_dpos_9{floor:02d}.narc"


def party_path(unpacked: Path, floor: int) -> Path:
    return unpacked / "data" / "yamada" / "DataBase" / f"db_party_9{floor:02d}.narc"


def read_stat_table(arm9: bytes, offset: int, maxcount: int) -> list[dict]:
    out = []
    for i in range(maxcount):
        off = offset + i * STAT_ENTRY
        if off + STAT_ENTRY > len(arm9):
            break
        e = unpack_struct(arm9[off:off + STAT_ENTRY], STAT_FIELDS)
        if e["model"] == 0xFFFF:  # Terminator, wie ihn die Lookup-Funktionen prüfen
            break
        out.append(e)
    return out


def read_tower(arm9: bytes) -> list[dict]:
    out = []
    for i in range(TOWER_COUNT):
        floor, map_id, echo = struct.unpack_from("<3H", arm9, TOWER_OFFSET + i * 6)
        out.append({"floor": floor, "map_id": map_id, "floor_echo": echo})
    return out


def read_floor(unpacked: Path, floor: int) -> dict | None:
    import ndspy.narc
    dp, pp = dpos_path(unpacked, floor), party_path(unpacked, floor)
    if not dp.exists() or not pp.exists():
        return None
    dpos = ndspy.narc.NARC.fromFile(str(dp))
    party = ndspy.narc.NARC.fromFile(str(pp))
    d0, p0 = dpos.files[0], party.files[0]
    n_d = len(d0) // DPOS_ENTRY
    enemies = [unpack_struct(d0[i * DPOS_ENTRY:(i + 1) * DPOS_ENTRY], DPOS_FIELDS)
               for i in range(n_d)]
    n_p = (len(p0) - PARTY_HEADER) // PARTY_ENTRY
    partners = [unpack_struct(p0[PARTY_HEADER + i * PARTY_ENTRY:PARTY_HEADER + (i + 1) * PARTY_ENTRY],
                              PARTY_FIELDS) for i in range(n_p)]
    return {
        "floor": floor,
        "enemies": enemies,
        "partners": partners,
        # Bytes, die nicht in Slots aufgehen, + weitere NARC-Subfiles
        "_dpos_tail": d0[n_d * DPOS_ENTRY:].hex(),
        "_party_header": p0[:PARTY_HEADER].hex(),
        "_party_tail": p0[PARTY_HEADER + n_p * PARTY_ENTRY:].hex(),
    }


def write_floor(unpacked: Path, fl: dict) -> None:
    import ndspy.narc
    floor = fl["floor"]
    dp, pp = dpos_path(unpacked, floor), party_path(unpacked, floor)
    dpos = ndspy.narc.NARC.fromFile(str(dp))
    party = ndspy.narc.NARC.fromFile(str(pp))
    new_d = (b"".join(pack_struct(e, DPOS_FIELDS, DPOS_ENTRY) for e in fl["enemies"])
             + bytes.fromhex(fl.get("_dpos_tail", "")))
    new_p = (bytes.fromhex(fl.get("_party_header", "01000000"))
             + b"".join(pack_struct(e, PARTY_FIELDS, PARTY_ENTRY) for e in fl["partners"])
             + bytes.fromhex(fl.get("_party_tail", "")))
    # Nur geänderte NARCs neu schreiben: ndspy padded den Header anders als das
    # Original, ein unnötiges Speichern würde die Datei verändern.
    for narc, path, new in ((dpos, dp, new_d), (party, pp, new_p)):
        if narc.files[0] != new:
            narc.files[0] = new
            narc.saveToFile(str(path))


def load_rom_data(unpacked: Path) -> dict:
    arm9 = (unpacked / "arm9.bin").read_bytes()
    data = {name: read_stat_table(arm9, off, n) for name, (off, n) in STAT_TABLES.items()}
    data["tower"] = read_tower(arm9)
    data["floors"] = {f: fl for f in FLOORS if (fl := read_floor(unpacked, f))}
    return data


def save_rom_data(unpacked: Path, data: dict) -> None:
    arm9_path = unpacked / "arm9.bin"
    arm9 = bytearray(arm9_path.read_bytes())
    for name, (off, maxcount) in STAT_TABLES.items():
        entries = data.get(name, [])
        if len(entries) > maxcount:
            raise ValueError(f"{name}: {len(entries)} Einträge > Maximum {maxcount}")
        for i, e in enumerate(entries):
            arm9[off + i * STAT_ENTRY:off + (i + 1) * STAT_ENTRY] = pack_struct(e, STAT_FIELDS, STAT_ENTRY)
    for i, t in enumerate(data.get("tower", [])):
        struct.pack_into("<3H", arm9, TOWER_OFFSET + i * 6, t["floor"], t["map_id"], t["floor_echo"])
    arm9_path.write_bytes(bytes(arm9))
    for fl in data.get("floors", {}).values():
        write_floor(unpacked, fl)


# --- JSON-Verzeichnis -------------------------------------------------------

def dump_json(data: dict, out: Path) -> None:
    (out / "floors").mkdir(parents=True, exist_ok=True)
    for key in (*STAT_TABLES, "tower"):
        (out / f"{key}.json").write_text(json.dumps(data[key], indent=1) + "\n")
    for f, fl in data["floors"].items():
        (out / "floors" / f"floor_{f:02d}.json").write_text(json.dumps(fl, indent=1) + "\n")


def load_json(src: Path) -> dict:
    data = {key: json.loads((src / f"{key}.json").read_text()) for key in (*STAT_TABLES, "tower")}
    data["floors"] = {}
    for p in sorted((src / "floors").glob("floor_*.json")):
        fl = json.loads(p.read_text())
        data["floors"][fl["floor"]] = fl
    return data


# --- Mods -----------------------------------------------------------------
# Mod-Format (alle Abschnitte optional, Schlüssel sind IDs/Nummern als String):
# {
#   "name": "Mein Mod",
#   "characters":    {"254": {"hp": 9999, "atk": 99}},
#   "characters_vs": {"3": {"hp": 5000}},
#   "tower":   {"7": {"map_id": 31}},
#   "floors":  {"9": {"enemies":  {"3": {"char_id": 181, "level": 80}},
#                     "partners": {"0": {"level": 50}}}}
# }

def _patch(target: dict, changes: dict, path: str, owners: dict, mod: str, log: list) -> None:
    for k, v in changes.items():
        if k.startswith("_"):
            raise ValueError(f"{mod}: {path}.{k} — Rohdaten (_*) sind in Mods nicht erlaubt")
        if k not in target:
            raise ValueError(f"{mod}: unbekanntes Feld {path}.{k}")
        key = f"{path}.{k}"
        prev = owners.get(key)
        if prev and prev[0] != mod and prev[1] != v:
            log.append(f"KONFLIKT {key}: {prev[0]}={prev[1]!r} wird von {mod}={v!r} überschrieben")
        owners[key] = (mod, v)
        target[k] = v


def apply_mod(data: dict, mod: dict, owners: dict, log: list) -> None:
    name = mod.get("name", "?")
    for table in STAT_TABLES:
        by_id = {e["id"]: e for e in data[table]}
        for cid, changes in mod.get(table, {}).items():
            if int(cid) not in by_id:
                raise ValueError(f"{name}: {table} ID {cid} existiert nicht")
            _patch(by_id[int(cid)], changes, f"{table}[{cid}]", owners, name, log)
    for floor, changes in mod.get("tower", {}).items():
        _patch(data["tower"][int(floor) - 1], changes, f"tower[{floor}]", owners, name, log)
    for floor, fmod in mod.get("floors", {}).items():
        fl = data["floors"].get(int(floor))
        if fl is None:
            raise ValueError(f"{name}: Floor {floor} nicht vorhanden")
        for kind in ("enemies", "partners"):
            for slot, changes in fmod.get(kind, {}).items():
                s = int(slot)
                if not 0 <= s < len(fl[kind]):
                    raise ValueError(f"{name}: Floor {floor} {kind} Slot {slot} existiert nicht "
                                     f"(neue Slots anlegen funktioniert im Spiel nicht zuverlässig)")
                _patch(fl[kind][s], changes, f"floors[{floor}].{kind}[{slot}]", owners, name, log)


# --- Validierung ----------------------------------------------------------

def validate(data: dict) -> list[str]:
    """Prüft auf die bekannten Crash-Ursachen aus docs/session-findings.md."""
    issues = []
    # flag1 ist eine Kategorie (6 z. B. bei Hollows), kein Aktiv-Flag — leer heißt HP und Level 0
    active = {e["id"] for e in data["characters"] if e["hp"] or e["level"]}
    for f, fl in sorted(data["floors"].items()):
        partner_ids = {p["char_id"] for p in fl["partners"] if p["type"] == 10}
        for i, e in enumerate(fl["enemies"]):
            cid = e["char_id"]
            if cid == 0:
                continue
            where = f"Floor {f} Slot {i}: char {cid}"
            if cid in BROKEN_IDS:
                issues.append(f"{where} ist als crashend bekannt")
            elif cid not in active:
                issues.append(f"{where} ist in der Stat-Tabelle leer (HP/Level 0)")
            if cid in partner_ids:
                issues.append(f"{where} ist gleichzeitig Partner auf diesem Floor (Crash)")
            if i >= DPOS_MAX_READ:
                issues.append(f"{where} liegt hinter Slot {DPOS_MAX_READ - 1} und wird nie gespawnt")
        wave0 = sum(1 for e in fl["enemies"][:DPOS_MAX_READ] if e["char_id"] and e["wave"] == 0)
        if wave0 > ACTOR_SLOTS - PARTY_SLOTS:
            issues.append(f"Floor {f}: {wave0} Gegner in Welle 0, aber nur {ACTOR_SLOTS} Aktor-Plätze "
                          f"(davon bis zu {PARTY_SLOTS} Party) — der Rest erscheint nicht")
    return issues


# --- CLI ------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--unpacked", type=Path, default=UNPACKED)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("export", help="unpacked/ → JSON")
    sp.add_argument("--out", type=Path, default=ROOT / "gamedata")
    sp = sub.add_parser("import", help="JSON → unpacked/")
    sp.add_argument("--src", type=Path, default=ROOT / "gamedata")
    sp = sub.add_parser("apply", help="Mods der Reihe nach auf unpacked/ anwenden")
    sp.add_argument("mods", nargs="+", type=Path)
    sp.add_argument("--dry-run", action="store_true")
    sub.add_parser("validate", help="bekannte Crash-Ursachen prüfen")
    a = p.parse_args(argv)

    if not (a.unpacked / "arm9.bin").exists():
        print(f"Fehlt: {a.unpacked / 'arm9.bin'} — erst ./tools/unpack.sh ausführen", file=sys.stderr)
        return 1

    if a.cmd == "export":
        data = load_rom_data(a.unpacked)
        dump_json(data, a.out)
        print(f"{len(data['characters'])} Chars, {len(data['characters_vs'])} VS-Chars, "
              f"{len(data['floors'])} Floors → {a.out}")
    elif a.cmd == "import":
        save_rom_data(a.unpacked, load_json(a.src))
        print(f"{a.src} → {a.unpacked}")
    elif a.cmd == "apply":
        data, owners, log = load_rom_data(a.unpacked), {}, []
        for m in a.mods:
            apply_mod(data, json.loads(m.read_text()), owners, log)
            print(f"angewendet: {m}")
        for line in log:
            print(line)
        issues = validate(data)
        for line in issues:
            print(f"WARNUNG: {line}")
        if not a.dry_run:
            save_rom_data(a.unpacked, data)
            print(f"geschrieben: {a.unpacked} — jetzt ./tools/repack.sh")
    elif a.cmd == "validate":
        issues = validate(load_rom_data(a.unpacked))
        for line in issues:
            print(f"WARNUNG: {line}")
        print(f"{len(issues)} Problem(e)")
        return 1 if issues else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
