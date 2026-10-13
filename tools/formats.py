"""Dateiformate des Spiels: BGSM (Text), NARC (Archiv), .inc (Klartext-Tabellen)."""
import struct, re


# ---------- BGSM: UTF-16LE Stringtabellen (db_*_name.bin, s_name.bin ...) ----------
def bgsm_strings(data):
    assert data[:4] == b'BGSM', 'kein BGSM'
    base = struct.unpack_from('<I', data, 0x0C)[0]
    count = struct.unpack_from('<I', data, 0x10)[0]
    out = {}
    for i in range(count):
        o = struct.unpack_from('<I', data, 0x14 + i * 4)[0]
        if o == 0xFFFFFFFF:
            continue
        o += base
        end = o
        while end + 1 < len(data) and data[end:end + 2] != b'\x00\x00':
            end += 2
        out[i] = data[o:end].decode('utf-16-le', 'replace')
    return out


def bgsm_replace_strings(data, new_strings):
    """BGSM mit geaenderten Strings neu packen. Gesamtgroesse bleibt exakt
    gleich (Rest wird genullt); wachsender Inhalt muss reinpassen.
    new_strings: {index: str} - nur die zu aendernden Eintraege."""
    base = struct.unpack_from('<I', data, 0x0C)[0]
    count = struct.unpack_from('<I', data, 0x10)[0]
    cur = bgsm_strings(data)
    for i, s in new_strings.items():
        if not 0 <= i < count:
            raise ValueError(f'BGSM-Index {i} ausserhalb 0..{count-1}')
        cur[i] = s
    out = bytearray(data[:0x14 + count * 4])
    off_by_str = {}     # identische Strings teilen sich einen Eintrag (wie Original)
    for i in range(count):
        if i not in cur:
            struct.pack_into('<I', out, 0x14 + i * 4, 0xFFFFFFFF)
            continue
        s = cur[i]
        if s not in off_by_str:
            off_by_str[s] = len(out) - base
            out += s.encode('utf-16-le') + b'\x00\x00'
        struct.pack_into('<I', out, 0x14 + i * 4, off_by_str[s])
    if len(out) > len(data):
        raise ValueError('BGSM wird zu gross - Namen kuerzen')
    out += b'\x00' * (len(data) - len(out))
    return bytes(out)


# ---------- NARC ----------
def narc_subfiles(data):
    assert data[:4] == b'NARC'
    nchunks = struct.unpack_from('<H', data, 0x0E)[0]
    pos, fat, img_off = 0x10, [], None
    for _ in range(nchunks):
        magic = data[pos:pos + 4]
        size = struct.unpack_from('<I', data, pos + 4)[0]
        if magic == b'BTAF':
            n = struct.unpack_from('<I', data, pos + 8)[0]
            fat = [struct.unpack_from('<II', data, pos + 12 + i * 8) for i in range(n)]
        elif magic == b'GMIF':
            img_off = pos + 8
        pos += size
    return [data[img_off + s:img_off + e] for s, e in fat]


def narc_replace_subfile(data, index, new_sub):
    """Subfile in einem NARC ersetzen (gleiche Groesse noetig)."""
    subs = narc_subfiles(data)
    if len(new_sub) != len(subs[index]):
        raise ValueError('Subfile-Groesse muss gleich bleiben')
    # GMIF-Offset erneut suchen
    nchunks = struct.unpack_from('<H', data, 0x0E)[0]
    pos, img_off, fat = 0x10, None, []
    for _ in range(nchunks):
        magic = data[pos:pos + 4]
        size = struct.unpack_from('<I', data, pos + 4)[0]
        if magic == b'BTAF':
            n = struct.unpack_from('<I', data, pos + 8)[0]
            fat = [struct.unpack_from('<II', data, pos + 12 + i * 8) for i in range(n)]
        elif magic == b'GMIF':
            img_off = pos + 8
        pos += size
    s, e = fat[index]
    return data[:img_off + s] + new_sub + data[img_off + e:]


def narc_rebuild(template, subfiles):
    """NARC komplett neu bauen: Header/BTNF vom Template, BTAF/GMIF aus den
    neuen Subfiles (Groessen DUERFEN sich aendern - anders als bei
    narc_replace_subfile). Subfile-Starts werden 4-aligned."""
    assert template[:4] == b'NARC'
    nchunks = struct.unpack_from('<H', template, 0x0E)[0]
    pos, btnf = 0x10, b''
    for _ in range(nchunks):
        magic = template[pos:pos + 4]
        size = struct.unpack_from('<I', template, pos + 4)[0]
        if magic == b'BTNF':
            btnf = template[pos:pos + size]
        pos += size
    assert btnf, 'Template ohne BTNF'
    # FAT + GMIF-Daten mit 4er-Alignment aufbauen
    fat, blobs, p = [], [], 0
    for s in subfiles:
        p = (p + 3) & ~3
        fat.append((p, p + len(s)))
        blobs.append((p, s))
        p += len(s)
    data_len = (p + 3) & ~3
    img = bytearray(b'\xff' * data_len)   # Alignment-Luecken wie im Original: 0xFF
    for off, s in blobs:
        img[off:off + len(s)] = s
    btaf = struct.pack('<4sII', b'BTAF', 12 + 8 * len(fat), len(fat))
    btaf += b''.join(struct.pack('<II', s, e) for s, e in fat)
    gmif = struct.pack('<4sI', b'GMIF', 8 + data_len) + bytes(img)
    total = 16 + len(btaf) + len(btnf) + len(gmif)
    hdr = bytearray(template[:0x10])
    struct.pack_into('<I', hdr, 0x08, total)
    return bytes(hdr) + btaf + btnf + gmif


# ---------- .inc: Klartext-Tabellen ({ 1, 2, {3, 4}, ... },) ----------
def parse_inc(text):
    """Parst die C-Initializer-Tabellen in verschachtelte int-Listen."""
    rows = []
    for m in re.finditer(r'\{(.*?)\},\s*$', text, re.M | re.S if False else re.M):
        pass
    # zeilenweise: jede Top-Level-Zeile beginnt mit '{' und endet mit '},'
    buf = ''
    depth = 0
    for ch in text:
        if ch == '{':
            depth += 1
        if depth > 0:
            buf += ch
        if ch == '}':
            depth -= 1
            if depth == 0:
                rows.append(_parse_group(buf))
                buf = ''
    return rows


def _parse_group(s):
    s = s.strip()
    assert s[0] == '{' and s[-1] == '}'
    s = s[1:-1]
    out, buf, depth = [], '', 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '{':
            j, d = i, 0
            while True:
                if s[j] == '{': d += 1
                elif s[j] == '}': d -= 1
                j += 1
                if d == 0: break
            out.append(_parse_group(s[i:j]))
            i = j
        elif ch in ',':
            if buf.strip():
                out.append(int(buf.strip()))
            buf = ''
            i += 1
        else:
            buf += ch
            i += 1
    if buf.strip():
        out.append(int(buf.strip()))
    return out


def format_inc(rows):
    """Serialisiert Zeilen zurueck ins .inc-Format (CRLF wie im Original)."""
    def fmt(v, top=False):
        if isinstance(v, list):
            inner = ', '.join(fmt(x) for x in v)
            return '{' + inner + (', ' if top else '') + '}'
        return str(v)
    lines = []
    for row in rows:
        inner = ', '.join(fmt(x) for x in row)
        lines.append('{ ' + inner + ',  },')
    return '\r\n'.join(lines) + '\r\n'
