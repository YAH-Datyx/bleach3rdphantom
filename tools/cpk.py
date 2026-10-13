"""CRI-CPK-Archive (z. B. /yamada/FIcon/tex.cpk): ITOC-basiert, Dateien
CRILAYLA-komprimiert (Magic hier ausgenullt). Minimal-Parser + Decompressor.

Aufbau pro Datei: 16-B-Header [8 B Magic(genullt) | u32 uncomp | u32 comp],
danach comp Bytes Bitstream (rueckwaerts), danach 0x100 Bytes Raw-Praefix
des Originals. Original = Praefix + rueckwaerts entpackter Rest.
"""
import struct


def _utf_read(data, off):
    """CRI-@UTF-Tabelle -> (name, rows als dicts). Big-Endian!"""
    assert data[off:off + 4] == b'@UTF', data[off:off + 4]
    base = off + 8
    (roff, soff, doff, name_off, nfield, rowlen, nrow) = \
        struct.unpack_from('>IIIIHHI', data, base)
    rows_off, str_off, data_off = base + roff, base + soff, base + doff

    def cstr(p):
        e = data.index(b'\0', str_off + p)
        return data[str_off + p:e].decode('ascii', 'replace')

    def val(p, typ):
        if typ in (0, 1):
            return data[p], p + 1
        if typ in (2, 3):
            return struct.unpack_from('>H', data, p)[0], p + 2
        if typ in (4, 5):
            return struct.unpack_from('>I', data, p)[0], p + 4
        if typ in (6, 7):
            return struct.unpack_from('>Q', data, p)[0], p + 8
        if typ == 8:
            return struct.unpack_from('>f', data, p)[0], p + 4
        if typ == 0xA:
            return cstr(struct.unpack_from('>I', data, p)[0]), p + 4
        if typ == 0xB:
            o, l = struct.unpack_from('>II', data, p)
            return ('DATA', data_off + o, l), p + 8
        raise ValueError(f'UTF-Typ {typ}')

    fields, p = [], base + 24
    for _ in range(nfield):
        flag = data[p]
        p += 1
        nm = ''
        if flag & 0x10:
            nm = cstr(struct.unpack_from('>I', data, p)[0])
            p += 4
        const = None
        if flag & 0x20:
            const, p = val(p, flag & 0x0F)
        fields.append((nm, flag & 0x0F, flag, const))
    rows = []
    for r in range(nrow):
        q = rows_off + r * rowlen
        row = {}
        for nm, typ, flag, const in fields:
            if flag & 0x20:
                row[nm] = const
            elif flag & 0x40:
                v, q = val(q, typ)
                row[nm] = v
        rows.append(row)
    return cstr(name_off), rows


def crilayla_decompress(blob):
    """Eine CPK-Datei (Header+Bitstream+Praefix) entpacken."""
    usize, csize = struct.unpack_from('<II', blob, 8)
    comp = blob[16:16 + csize]
    prefix = blob[16 + csize:16 + csize + 0x100]
    out = bytearray(usize)
    opos = usize
    state = {'ipos': len(comp), 'pool': 0, 'bits': 0}

    def getbits(n):
        v = 0
        while n:
            if state['bits'] == 0:
                state['ipos'] -= 1
                state['pool'] = comp[state['ipos']]
                state['bits'] = 8
            take = min(n, state['bits'])
            v = (v << take) | ((state['pool'] >> (state['bits'] - take))
                               & ((1 << take) - 1))
            state['bits'] -= take
            n -= take
        return v

    while opos > 0:
        if getbits(1):
            offset = getbits(13) + 3
            refc = 3
            lv = getbits(2)
            refc += lv
            if lv == 3:
                lv = getbits(3)
                refc += lv
                if lv == 7:
                    lv = getbits(5)
                    refc += lv
                    if lv == 31:
                        while True:
                            lv = getbits(8)
                            refc += lv
                            if lv != 255:
                                break
            for _ in range(refc):
                out[opos - 1] = out[opos - 1 + offset]
                opos -= 1
        else:
            out[opos - 1] = getbits(8)
            opos -= 1
    return prefix + bytes(out)


def cpk_files(data):
    """-> {datei_id: entpackte Bytes} eines ITOC-CPKs."""
    _, hdr = _utf_read(data, 0x10)
    hdr = hdr[0]
    content, align = hdr['ContentOffset'], hdr['Align']
    _, itoc = _utf_read(data, hdr['ItocOffset'] + 0x10)
    out = {}
    entries = []
    for tag in ('DataL', 'DataH'):
        blob = itoc[0].get(tag)
        if isinstance(blob, tuple) and blob[0] == 'DATA' and blob[2]:
            _, rows = _utf_read(data, blob[1])
            entries += [(r['ID'], r['FileSize'], r['ExtractSize']) for r in rows]
    pos = content
    for fid, fsize, xsize in sorted(entries):
        blob = data[pos:pos + fsize]
        if fsize == xsize:
            out[fid] = blob
        else:
            out[fid] = crilayla_decompress(blob)
            assert len(out[fid]) == xsize, (fid, len(out[fid]), xsize)
        pos += fsize
        if pos % align:
            pos += align - pos % align
    return out
