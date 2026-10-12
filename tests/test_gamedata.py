"""Tests für tools/scripts/gamedata.py mit synthetischen Daten (keine ROM nötig).

  python3 -m pytest tests/
"""
import json, struct, sys
from pathlib import Path

import ndspy.narc
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "scripts"))
import gamedata as gd


@pytest.fixture
def unpacked(tmp_path):
    tmp_path = tmp_path / "unpacked"
    tmp_path.mkdir()
    arm9 = bytearray(0x110000)
    off = gd.STAT_TABLES["characters"][0]
    for i in range(255):
        o = off + i * gd.STAT_ENTRY
        # model (0x00) weicht teils von der ID (0x02) ab, wie im echten ROM bei Eintrag 6
        struct.pack_into("<HHBBBBHH4B", arm9, o, i or 1, i + 1, 1, 1, 2, 10, 500 + i, 50, 20, 21, 22, 23)
        arm9[o + 0x10] = 3  # unbekanntes Byte, muss erhalten bleiben
    struct.pack_into("<HH", arm9, off + 255 * gd.STAT_ENTRY, 0xFFFF, 0xFFFF)
    for i in range(gd.TOWER_COUNT):
        struct.pack_into("<3H", arm9, gd.TOWER_OFFSET + i * 6, i + 1, i + 2, i + 1)
    (tmp_path / "arm9.bin").write_bytes(arm9)
    db = tmp_path / "data" / "yamada" / "DataBase"
    db.mkdir(parents=True)
    for f in (9, 14):
        d = bytearray(gd.DPOS_ENTRY * 4 + 2)
        struct.pack_into("<8H", d, 0, 784, 154, 80, 15, 3, 4, 2, 1)
        struct.pack_into("<8H", d, gd.DPOS_ENTRY, 785, 21, 30, 10, 5, 6, 2, 1)
        d[-2:] = b"\xab\xcd"
        p = bytearray(b"\x01\x00\x00\x00") + struct.pack("<7H", 10, 30, 21, 2, 1, 2, 0)
        for path, payload in ((gd.dpos_path(tmp_path, f), d), (gd.party_path(tmp_path, f), p)):
            narc = ndspy.narc.NARC()
            narc.files = [bytes(payload), b"other-subfile"]
            narc.saveToFile(str(path))
    return tmp_path


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_import_unchanged_keeps_narc_files_untouched(unpacked, tmp_path):
    # ndspy würde den NARC-Header anders padden — unveränderte Dateien bleiben unberührt
    p = gd.dpos_path(unpacked, 9)
    p.write_bytes(p.read_bytes() + b"\0" * 4)
    before = p.read_bytes()
    gd.save_rom_data(unpacked, gd.load_rom_data(unpacked))
    assert p.read_bytes() == before


def test_roundtrip_is_byte_identical(unpacked, tmp_path):
    before = snapshot(unpacked)
    out = tmp_path / "json"
    gd.dump_json(gd.load_rom_data(unpacked), out)
    gd.save_rom_data(unpacked, gd.load_json(out))
    assert snapshot(unpacked) == before


def test_export_contents(unpacked):
    data = gd.load_rom_data(unpacked)
    assert len(data["characters"]) == 255
    assert data["characters"][1]["model"] == 1 and data["characters"][1]["id"] == 2
    assert data["characters"][0]["hp"] == 500
    assert data["tower"][6] == {"floor": 7, "map_id": 8, "floor_echo": 7}
    assert sorted(data["floors"]) == [9, 14]
    assert data["floors"][9]["enemies"][0]["char_id"] == 154
    assert data["floors"][9]["partners"][0]["char_id"] == 21


def test_apply_mod_and_conflicts(unpacked):
    data, owners, log = gd.load_rom_data(unpacked), {}, []
    gd.apply_mod(data, {"name": "a", "characters": {"254": {"hp": 9999}},
                        "floors": {"9": {"enemies": {"0": {"char_id": 181}}}}}, owners, log)
    gd.apply_mod(data, {"name": "b", "characters": {"254": {"hp": 1234}},
                        "tower": {"7": {"map_id": 31}}}, owners, log)
    gd.save_rom_data(unpacked, data)
    again = gd.load_rom_data(unpacked)
    assert again["characters"][253]["hp"] == 1234
    assert again["tower"][6]["map_id"] == 31
    assert again["floors"][9]["enemies"][0]["char_id"] == 181
    assert len(log) == 1 and "KONFLIKT" in log[0]


@pytest.mark.parametrize("mod", [
    {"characters": {"254": {"bogus": 1}}},
    {"characters": {"254": {"_raw": "00"}}},
    {"floors": {"9": {"enemies": {"99": {"level": 1}}}}},
    {"floors": {"3": {}}},
])
def test_apply_rejects_invalid(unpacked, mod):
    with pytest.raises(ValueError):
        gd.apply_mod(gd.load_rom_data(unpacked), mod, {}, [])


def test_validate(unpacked):
    data = gd.load_rom_data(unpacked)
    issues = gd.validate(data)
    # char 21 ist auf Floor 9 und 14 zugleich Partner und Gegner
    assert len(issues) == 2 and all("Partner" in i for i in issues)
    data["floors"][9]["enemies"][0]["char_id"] = 175
    assert any("crashend" in i for i in gd.validate(data))


def test_cli_export_apply(unpacked, tmp_path):
    out = tmp_path / "json"
    assert gd.main(["--unpacked", str(unpacked), "export", "--out", str(out)]) == 0
    assert json.loads((out / "floors" / "floor_09.json").read_text())["floor"] == 9
    mod = tmp_path / "m.json"
    mod.write_text(json.dumps({"name": "m", "characters": {"1": {"atk": 99}}}))
    assert gd.main(["--unpacked", str(unpacked), "apply", str(mod)]) == 0
    assert gd.load_rom_data(unpacked)["characters"][0]["atk"] == 99
