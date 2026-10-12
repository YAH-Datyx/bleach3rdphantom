"""NCER/NANR-Parser + Writer, Animations-Tool und CPK.

Synthetische Tests laufen ohne ROM. Die Tests gegen echte Daten werden
übersprungen, wenn unpacked-decomp/ fehlt.
"""
import json, struct, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "re"))
sys.path.insert(0, str(ROOT / "tools" / "scripts"))
import nitro_anim as na  # noqa: E402

DEC = ROOT / "unpacked-decomp" / "data"
needs_rom = pytest.mark.skipif(not DEC.exists(), reason="unpacked-decomp/ fehlt (ROM nicht entpackt)")


def nitro(magic: bytes, sections: list[tuple[bytes, bytes]]) -> bytes:
    hdr = magic + b"\xff\xfe\x00\x01" + bytes(4) + struct.pack("<HH", 0x10, len(sections))
    return na.join_sections(hdr, sections)


def make_ncer() -> bytes:
    oam = struct.pack("<3H", 0x00F8, 0x41F0, 0x1004) + struct.pack("<3H", 0x8000, 0x0008, 0x0000)
    cells = struct.pack("<HHI", 2, 0, 0) + struct.pack("<HHI", 1, 0, 6)
    kbec = struct.pack("<HHIIIII", 2, 0, 0x18, 0, 0, 0, 0) + cells + oam
    return nitro(b"RECN", [(b"KBEC", kbec)])


def make_nanr() -> bytes:
    seq = struct.pack("<HHHHII", 3, 0, 0, 1, 2, 0)
    frames = b"".join(struct.pack("<IHH", o, 5, 0xBEEF) for o in (0, 2, 0))
    data = struct.pack("<HH", 0, 1)
    knba = struct.pack("<HHIII", 1, 3, 0x18, 0x28, 0x40) + bytes(8) + seq + frames + data
    return nitro(b"RNAN", [(b"KNBA", knba)])


def test_oam_decode_encode_roundtrip():
    for a in [(0x00F8, 0x41F0, 0x1004), (0x8000, 0x3008, 0xF3FF), (0x4100, 0xC0FF, 0x0123)]:
        assert na.encode_oam(na.decode_oam(*a)) == a


def test_oam_fields():
    o = na.decode_oam(0x00F8, 0x41F0, 0x1004)
    assert (o["x"], o["y"], o["w"], o["h"], o["tile"], o["palette"]) == (-16, -8, 16, 16, 4, 1)


@pytest.mark.parametrize("make,parse,build", [(make_ncer, na.parse_ncer, na.build_ncer),
                                              (make_nanr, na.parse_nanr, na.build_nanr)])
def test_synthetic_roundtrip_via_json(make, parse, build):
    raw = make()
    assert build(json.loads(json.dumps(parse(raw)))) == raw


def test_nanr_edit_rebuilds_frame_data():
    n = na.parse_nanr(make_nanr())
    s = n["sequences"][0]
    assert [f["cell"] for f in s["frames"]] == [0, 1, 0]
    s["frames"].append({"cell": 1, "duration": 9})              # neuer Frame ohne Rohdaten
    n["sequences"].append({"loop_start": 0, "elem_type": 0, "anim_type": 1, "play_mode": 2,
                           "frames": [{"cell": 0, "duration": 3}]})  # neue Sequenz
    again = na.parse_nanr(na.build_nanr(n))
    assert [(f["cell"], f["duration"]) for f in again["sequences"][0]["frames"]] == [(0, 5), (1, 5), (0, 5), (1, 9)]
    assert [(f["cell"], f["duration"]) for f in again["sequences"][1]["frames"]] == [(0, 3)]


def test_ncer_edit_adds_cell_and_oam():
    c = na.parse_ncer(make_ncer())
    c["cells"].append({"attr": 0, "oam": [dict(c["cells"][0]["oam"][0], x=5, tile=9)]})
    again = na.parse_ncer(na.build_ncer(c))
    assert len(again["cells"]) == 3
    assert again["cells"][2]["oam"][0]["x"] == 5 and again["cells"][2]["oam"][0]["tile"] == 9


def test_tiles_png_roundtrip():
    import anim
    chars = bytes(range(256)) * 2  # 16 Tiles 4-bit
    img = anim.tiles_to_image(chars, 4, [(i, i, i) for i in range(16)])
    assert anim.image_to_tiles(img, 4, 16) == chars


@needs_rom
def test_all_rom_cells_and_animations_roundtrip():
    import ndspy.narc
    n = 0
    for f in DEC.rglob("*"):
        if not f.is_file():
            continue
        b = f.read_bytes()
        parts = list(ndspy.narc.NARC(b).files) if b[:4] == b"NARC" else [b]
        for p in parts:
            if p[:4] == b"RECN":
                assert na.build_ncer(json.loads(json.dumps(na.parse_ncer(p)))) == p, f
                n += 1
            elif p[:4] == b"RNAN":
                assert na.build_nanr(json.loads(json.dumps(na.parse_nanr(p)))) == p, f
                n += 1
    assert n > 1000


@needs_rom
def test_all_cpk_rebuild_identical():
    import cpk
    paths = sorted(DEC.rglob("*.cpk"))
    assert paths
    for p in paths:
        c = cpk.read_cpk(p)
        assert cpk.build_cpk(c, {}) == c["_bytes"], p
        for f in c["files"]:
            assert len(cpk.file_data(c, f)) == f["extract"], (p, f["id"])
