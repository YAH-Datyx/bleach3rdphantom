#!/usr/bin/env python3
"""Konvertiert Nitro-2D-Grafik (NCLR + NCGR [+ NSCR]) nach PNG.

Funktioniert mit losen Dateien und mit (Huffman-komprimierten) NARCs, wie sie in
FMap/, NCface/, Status/, kuro/nc_main/ usw. liegen. Ausgabe nur lokal (z. B.
build/png/) — extrahierte Grafiken sind Eigentum der Rechteinhaber und gehören
nicht ins Repo.

  python3 tools/re/nitro2png.py <datei.bin|.narc> [out-dir]
"""
import struct, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from decompress import decompress_huffman  # noqa: E402


def section(data: bytes, magic: bytes) -> bytes:
    hsize = struct.unpack_from("<H", data, 0x0C)[0]
    pos = hsize
    while pos + 8 <= len(data):
        m, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        if m == magic:
            return data[pos:pos + size]
        pos += size
    raise ValueError(f"Sektion {magic!r} fehlt")


def parse_nclr(data: bytes) -> list[tuple[int, int, int]]:
    s = section(data, b"TTLP")
    size, off = struct.unpack_from("<II", s, 0x10)
    raw = s[0x18:0x18 + size]
    cols = []
    for (c,) in struct.iter_unpack("<H", raw[:len(raw) // 2 * 2]):
        cols.append(((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31))
    return cols


def parse_ncgr(data: bytes):
    s = section(data, b"RAHC")
    h, w, depth = struct.unpack_from("<HHI", s, 8)
    size, off = struct.unpack_from("<II", s, 0x18)
    bpp = 4 if depth == 3 else 8
    raw = s[8 + off:8 + off + size]
    tiles = []
    step = 8 * bpp
    for t in range(len(raw) // step):
        chunk = raw[t * step:(t + 1) * step]
        if bpp == 8:
            px = list(chunk)
        else:
            px = [v for b in chunk for v in (b & 15, b >> 4)]
        tiles.append(px)
    return tiles, bpp, (w if w != 0xFFFF else 0, h if h != 0xFFFF else 0)


def parse_nscr(data: bytes):
    s = section(data, b"NRCS")
    w, h = struct.unpack_from("<HH", s, 8)
    size = struct.unpack_from("<I", s, 0x10)[0]
    return w, h, [e for (e,) in struct.iter_unpack("<H", s[0x14:0x14 + size])]


def render_tilemap(tiles, bpp, pal, w, h, entries) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for i, e in enumerate(entries):
        tx, ty = (i % (w // 8)) * 8, (i // (w // 8)) * 8
        if ty >= h:
            break
        t = e & 0x3FF
        if t >= len(tiles):
            continue
        tile, hf, vf, pb = tiles[t], e >> 10 & 1, e >> 11 & 1, (e >> 12) * 16 if bpp == 4 else 0
        for y in range(8):
            for x in range(8):
                v = tile[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
                c = pal[pb + v] if pb + v < len(pal) else (255, 0, 255)
                px[tx + x, ty + y] = (*c, 0 if v == 0 else 255)
    return img


def render_tiles(tiles, bpp, pal, w_tiles) -> Image.Image:
    w_tiles = w_tiles or 16
    rows = (len(tiles) + w_tiles - 1) // w_tiles
    img = Image.new("RGBA", (w_tiles * 8, rows * 8))
    px = img.load()
    for t, tile in enumerate(tiles):
        tx, ty = (t % w_tiles) * 8, (t // w_tiles) * 8
        for i, v in enumerate(tile):
            c = pal[v] if v < len(pal) else (255, 0, 255)
            px[tx + i % 8, ty + i // 8] = (*c, 0 if v == 0 else 255)
    return img


def load_parts(path: Path) -> list[bytes]:
    data = path.read_bytes()
    if data[:1] in (b"\x24", b"\x28"):
        data = decompress_huffman(data)
    if data[:4] == b"NARC":
        import ndspy.narc
        return list(ndspy.narc.NARC(data).files)
    return [data]


def convert(path: Path, out: Path) -> list[Path]:
    parts = load_parts(path)
    pals = [parse_nclr(p) for p in parts if p[:4] == b"RLCN"]
    gfx = [p for p in parts if p[:4] == b"RGCN"]
    maps = [p for p in parts if p[:4] == b"RCSN"]
    if not pals or not gfx:
        raise ValueError("braucht mindestens NCLR + NCGR")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for i, g in enumerate(gfx):
        tiles, bpp, (w, h) = parse_ncgr(g)
        pal = pals[min(i, len(pals) - 1)]
        if i < len(maps):
            mw, mh, entries = parse_nscr(maps[i])
            img = render_tilemap(tiles, bpp, pal, mw, mh, entries)
        else:
            img = render_tiles(tiles, bpp, pal, w)
        p = out / f"{path.stem}_{i}.png"
        img.save(p)
        written.append(p)
    return written


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("build/png")
    for p in convert(src, dst):
        print(p)
