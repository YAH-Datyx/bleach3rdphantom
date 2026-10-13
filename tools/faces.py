"""Charakter-Portraits (/yamada/NCface/nc_FFFVV.bin) dekodieren.

Kette: BIOS-Huffman(0x28) -> NARC -> [NCGR-Tiles 8bpp, NCLR-Palette BGR555]
liefert PNG-Bytes (fuer tkinter PhotoImage direkt verwendbar).
"""
import struct, zlib, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from formats import narc_subfiles


def huff_decompress(data):
    hdr = struct.unpack_from('<I', data, 0)[0]
    assert (hdr & 0xF0) == 0x20, f'kein Huffman: {hdr & 0xFF:#x}'
    bits = hdr & 0x0F
    out_size = hdr >> 8
    tree_size = data[4]
    out = bytearray()
    node_addr = 5
    pos = 4 + (tree_size + 1) * 2
    nib = []
    while len(out) < out_size and pos + 4 <= len(data):
        w = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        for b in range(31, -1, -1):
            bit = (w >> b) & 1
            node = data[node_addr]
            child = (node_addr & ~1) + (node & 0x3F) * 2 + 2 + bit
            if node & (0x80 >> bit):
                sym = data[child]
                if bits == 8:
                    out.append(sym)
                else:
                    nib.append(sym & 0xF)
                    if len(nib) == 2:
                        out.append(nib[0] | (nib[1] << 4)); nib = []
                node_addr = 5
                if len(out) >= out_size:
                    break
            else:
                node_addr = child
    return bytes(out[:out_size])


def _chunk(data, magic):
    pos = 16  # nach Nitro-Header
    while pos + 8 <= len(data):
        m = data[pos:pos + 4]
        size = struct.unpack_from('<I', data, pos + 4)[0]
        if m == magic:
            return pos, size
        pos += size
    raise ValueError(f'{magic} nicht gefunden')


def decode_ncgr(data):
    """-> (breite, hoehe, pixel-indizes als bytes); NCface nutzt lineares 8bpp-Bitmap."""
    pos, size = _chunk(data, b'RAHC')
    th, tw, depth = struct.unpack_from('<HHI', data, pos + 8)
    dsize, doff = struct.unpack_from('<II', data, pos + 24)
    px_data = data[pos + 8 + doff:pos + 8 + doff + dsize]
    w, h = tw * 8, th * 8
    if depth == 4:      # 8bpp linear
        return w, h, bytes(px_data[:w * h])
    # 4bpp linear -> auf 8bpp expandieren
    out = bytearray()
    for b in px_data:
        out.append(b & 0xF)
        out.append(b >> 4)
    return w, h, bytes(out[:w * h])


def decode_nclr(data):
    pos, size = _chunk(data, b'TTLP')
    dsize = struct.unpack_from('<I', data, pos + 16)[0]
    off = pos + 24
    pal = []
    for i in range(min(dsize, size - 24) // 2):
        c = struct.unpack_from('<H', data, off + i * 2)[0]
        r = (c & 31) << 3; g = ((c >> 5) & 31) << 3; b = ((c >> 10) & 31) << 3
        pal.append((r | r >> 5, g | g >> 5, b | b >> 5))
    return pal


def to_png(w, h, idx, pal):
    """indizierte Pixel -> RGBA-PNG (Farbe 0 = transparent)"""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            p = idx[y * w + x]
            r, g, b = pal[p] if p < len(pal) else (255, 0, 255)
            raw += bytes((r, g, b, 0 if p == 0 else 255))
    def ch(tag, body):
        c = tag + body
        return struct.pack('>I', len(body)) + c + struct.pack('>I', zlib.crc32(c))
    return (b'\x89PNG\r\n\x1a\n'
            + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(bytes(raw), 6))
            + ch(b'IEND', b''))


def face_png(fs, face_id, variant=1, crop=64):
    """PNG des Portraits (linker crop x hoehe Ausschnitt), None wenn nicht vorhanden."""
    path = f'/yamada/NCface/nc_{face_id:03d}{variant:02d}.bin'
    if path not in fs.by_path:
        return None
    try:
        narc = huff_decompress(fs.read(path))
        subs = narc_subfiles(narc)
        w, h, idx = decode_ncgr(subs[0])
        pal = decode_nclr(subs[1])
    except Exception:
        return None
    if crop and crop < w:
        idx = b''.join(idx[y * w:y * w + crop] for y in range(h))
        w = crop
    return to_png(w, h, idx, pal)


if __name__ == '__main__':
    from romfs import RomFS
    fs = RomFS()
    png = face_png(fs, int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    out = sys.argv[3] if len(sys.argv) > 3 else 'face.png'
    open(out, 'wb').write(png)
    print(out, 'geschrieben')
