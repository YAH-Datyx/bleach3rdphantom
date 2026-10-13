"""Spielfeld-Karten (/yamada/FMap/MAPxxx.bin) dekodieren und als PNG rendern.

MAPxxx.bin = BIOS-Huffman -> NARC:
  sub0 RGCN  Tileset (8x8-Tiles, 8bpp)
  sub1 RLCN  16 erweiterte Paletten a 256 Farben
  sub2 RCSN  Tilemap (Feld, Breite/Hoehe in px variieren pro Map)
  sub3 RNAN / sub4 RGCN / sub5 RECN  Animationen/Marker
  sub6 RLCN  Zusatzpalette

Map-ID (db_btower Spalte 2, db_fbattle Spalte 4) -> Dateinummer via MAP_TABLE
(aus ARM9-Overlay 1, 0x3ada8; 0-basiert indiziert).
"""
import struct, sys, os, zlib

sys.path.insert(0, os.path.dirname(__file__))
from formats import narc_subfiles
from faces import huff_decompress, decode_nclr, _chunk

# Overlay1 @0x3ada8: Map-ID -> MAPxxx-Dateinummer (65535/fehlend = ungenutzt)
MAP_TABLE = [11, 21, 31, 32, 41, 51, 61, 71, 81, 82, 91, 92, 101, 111, 121,
             131, 141, 151, 161, 162, 171, 181, 191, 192, 193, 201, 221, 222,
             231, 232, 241, 251, 252, 271, 291, 321, 331, 351, 361, 381]


def map_file_for_id(map_id):
    if 0 <= map_id < len(MAP_TABLE):
        return MAP_TABLE[map_id]
    return None


def decode_map(fs, file_no):
    """-> (breite_px, hoehe_px, RGB-Bytes) des Spielfelds."""
    narc = huff_decompress(fs.read(f'/yamada/FMap/MAP{file_no:03d}.bin'))
    subs = narc_subfiles(narc)
    tiles = pals = scr = None
    for s in subs:
        if s[:4] == b'RGCN' and tiles is None:
            pos, _ = _chunk(s, b'RAHC')
            dsize, doff = struct.unpack_from('<II', s, pos + 24)
            tiles = s[pos + 8 + doff:pos + 8 + doff + dsize]
        elif s[:4] == b'RLCN' and pals is None:
            pals = decode_nclr(s)          # bis zu 16*256 Farben
        elif s[:4] == b'RCSN':
            w, h = struct.unpack_from('<HH', s, 24)
            dsz = struct.unpack_from('<I', s, 32)[0]
            scr = (w, h, s[36:36 + dsz])
    w, h, ents = scr
    tw, th = w // 8, h // 8
    img = bytearray(w * h * 3)
    ntiles = len(tiles) // 64
    # NSCR > 256px ist in 256x256-Screenbloecken abgelegt (je 32x32 Tiles,
    # Randbloecke schmaler), Bloecke zeilenweise, innerhalb row-major.
    order = []
    for by in range(0, th, 32):
        for bx in range(0, tw, 32):
            bw, bh = min(32, tw - bx), min(32, th - by)
            for y in range(bh):
                for x in range(bw):
                    order.append((bx + x, by + y))
    for i in range(len(ents) // 2):
        e = struct.unpack_from('<H', ents, i * 2)[0]
        tid = e & 0x3FF
        hflip = e & 0x400
        vflip = e & 0x800
        pal = (e >> 12) & 0xF
        cx, cy = order[i]
        tx, ty = cx * 8, cy * 8
        if tid >= ntiles:
            continue
        tile = tiles[tid * 64:tid * 64 + 64]
        for py in range(8):
            sy = 7 - py if vflip else py
            for px in range(8):
                sx = 7 - px if hflip else px
                ci = tile[sy * 8 + sx]
                c = pal * 256 + ci
                r, g, b = pals[c] if c < len(pals) else (255, 0, 255)
                o = ((ty + py) * w + tx + px) * 3
                img[o:o + 3] = bytes((r, g, b))
    return w, h, bytes(img)


def rgb_to_png(w, h, rgb):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y * w * 3:(y + 1) * w * 3]
    def ch(tag, body):
        c = tag + body
        return struct.pack('>I', len(body)) + c + struct.pack('>I', zlib.crc32(c))
    return (b'\x89PNG\r\n\x1a\n'
            + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(bytes(raw), 6))
            + ch(b'IEND', b''))


def map_png(fs, map_id):
    """PNG des Spielfelds fuer eine Map-ID, None wenn Datei fehlt."""
    fn = map_file_for_id(map_id)
    if fn is None or f'/yamada/FMap/MAP{fn:03d}.bin' not in fs.by_path:
        return None
    w, h, rgb = decode_map(fs, fn)
    return rgb_to_png(w, h, rgb)


if __name__ == '__main__':
    from romfs import RomFS
    fs = RomFS()
    map_id = int(sys.argv[1])
    png = map_png(fs, map_id)
    out = sys.argv[2] if len(sys.argv) > 2 else f'map_{map_id}.png'
    open(out, 'wb').write(png)
    print(out, 'geschrieben')
