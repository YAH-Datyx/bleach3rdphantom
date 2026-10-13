"""Bleach 3rd Phantom - MOBILER Editor (Pythonista / Pyto / a-Shell auf iOS).

EINE Datei, KEINE Abhaengigkeiten. Legt die .nds direkt (in-place).
Menuegesteuert ueber die Konsole - laeuft genauso auf dem PC.

ROM finden: der ROM-Pfad wird automatisch gesucht (iCloud/Ordner der
Datei). Notfalls unten ROM_PATH von Hand setzen.

Funktionen: Etage anzeigen | randomisieren (Level+Anzahl) | Skillpoints
setzen | GOD-MODE. Positionen bleiben auf begehbaren Feldern, Gegner
schauen zur Deploy-Zone, Sprite-Limit 25 wird beachtet.
"""
import os, struct, random, glob

# ---------------------------------------------------------------- ROM finden
ROM_NAME = 'Bleach3P modded.nds'
ROM_PATH = None   # <- hier bei Bedarf manuell einen vollen Pfad eintragen

def find_rom():
    if ROM_PATH and os.path.exists(ROM_PATH):
        return ROM_PATH
    cands = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ROM_NAME),
        os.path.expanduser('~/Documents/' + ROM_NAME),
        os.path.expanduser('~/Documents/Modded ROM files/' + ROM_NAME),
    ]
    # iCloud Drive (iOS Pythonista/Pyto) + Windows-Fallback
    cands += glob.glob(os.path.expanduser('~/**/Modded ROM files/' + ROM_NAME), recursive=True)
    cands.append(r"C:\Users\danie\OneDrive - Technische Hochschule Rosenheim\Desktop\Bleach3P_RE\Bleach3P modded.nds")
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None

# ---------------------------------------------------------------- NDS/NARC
def read_header(f):
    f.seek(0); h = f.read(0x200)
    return {'fnt_off': struct.unpack_from('<I', h, 0x40)[0],
            'fnt_size': struct.unpack_from('<I', h, 0x44)[0],
            'fat_off': struct.unpack_from('<I', h, 0x48)[0],
            'fat_size': struct.unpack_from('<I', h, 0x4C)[0]}

def parse_fnt(f, off, size):
    f.seek(off); fnt = f.read(size); files = {}
    def walk(did, path):
        so, ff = struct.unpack_from('<IH', fnt, (did & 0xFFF) * 8)
        pos, fid = so, ff
        while True:
            ln = fnt[pos]; pos += 1
            if ln == 0: break
            nm = fnt[pos:pos + (ln & 0x7F)].decode('ascii', 'replace'); pos += ln & 0x7F
            if ln & 0x80:
                sid = struct.unpack_from('<H', fnt, pos)[0]; pos += 2
                walk(sid, path + nm + '/')
            else:
                files[fid] = path + nm; fid += 1
    walk(0xF000, '/'); return files

class Rom:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.hdr = read_header(f)
            self.files = parse_fnt(f, self.hdr['fnt_off'], self.hdr['fnt_size'])
            f.seek(self.hdr['fat_off']); d = f.read(self.hdr['fat_size'])
            self.fat = [struct.unpack_from('<II', d, i * 8) for i in range(len(d) // 8)]
        self.by = {p: i for i, p in self.files.items()}
        self.size = os.path.getsize(path); self.free = (max(e for _, e in self.fat) + 3) & ~3
    def read(self, p):
        s, e = self.fat[self.by[p]]
        with open(self.path, 'rb') as f: f.seek(s); return f.read(e - s)
    def write(self, p, data):
        fid = self.by[p]; s, e = self.fat[fid]; slot = e - s
        fe = self.hdr['fat_off'] + fid * 8
        with open(self.path, 'r+b') as f:
            if len(data) <= slot:
                f.seek(s); f.write(data.ljust(slot, b'\0'))
                if len(data) != slot: f.seek(fe + 4); f.write(struct.pack('<I', s + len(data)))
            else:
                ns = self.free; self.free = (ns + len(data) + 3) & ~3
                f.seek(ns); f.write(data)
                f.seek(fe); f.write(struct.pack('<II', ns, ns + len(data)))
                f.seek(0x80); used = struct.unpack('<I', f.read(4))[0]
                if ns + len(data) > used: f.seek(0x80); f.write(struct.pack('<I', ns + len(data)))
                self.fat[fid] = (ns, ns + len(data))

def narc_subs(data):
    n = struct.unpack_from('<H', data, 0x0E)[0]; pos = 0x10; fat = []; img = None
    for _ in range(n):
        mg = data[pos:pos + 4]; sz = struct.unpack_from('<I', data, pos + 4)[0]
        if mg == b'BTAF':
            k = struct.unpack_from('<I', data, pos + 8)[0]
            fat = [struct.unpack_from('<II', data, pos + 12 + i * 8) for i in range(k)]
        elif mg == b'GMIF': img = pos + 8
        pos += sz
    return [data[img + s:img + e] for s, e in fat], img, fat

def narc_replace(data, idx, new):
    subs, img, fat = narc_subs(data)
    s, e = fat[idx]; assert len(new) == e - s
    return data[:img + s] + new + data[img + e:]

# ---------------------------------------------------------------- dpos
REC = 54
def bgsm(data):
    base = struct.unpack_from('<I', data, 0x0C)[0]; cnt = struct.unpack_from('<I', data, 0x10)[0]
    out = {}
    for i in range(cnt):
        o = struct.unpack_from('<I', data, 0x14 + i * 4)[0]
        if o == 0xFFFFFFFF: continue
        o += base; e = o
        while e + 1 < len(data) and data[e:e + 2] != b'\0\0': e += 2
        out[i] = data[o:e].decode('utf-16-le', 'replace')
    return out

def floor_units(rom, fl):
    sub = narc_subs(rom.read(f'/yamada/DataBase/db_dpos_{900+fl}.narc'))[0][0]
    out = []
    for r in range(len(sub) // REC):
        rec = sub[r * REC:(r + 1) * REC]; f = struct.unpack('<26H', rec[2:])
        if not any(f): continue
        out.append({'slot': rec[0], 'active': rec[1], 'char': f[0], 'level': f[1],
                    'x': f[3], 'y': f[4], 'dir': f[5], 'raw': list(f[7:])})
    return out

def pack_units(rom, fl, units):
    data = rom.read(f'/yamada/DataBase/db_dpos_{900+fl}.narc')
    subs = narc_subs(data)[0]; sub = bytearray(subs[0])
    for r in range(len(sub) // REC):
        sub[r * REC + 2:(r + 1) * REC] = b'\0' * (REC - 2)
    for u in units:
        r = u['slot'] - 1
        sub[r * REC:(r + 1) * REC] = struct.pack('<BB26H', u['slot'], u.get('active', 3),
            u['char'], u['level'], u.get('unk3', 10), u['x'], u['y'], u.get('dir', 0),
            u.get('unk7', 1), *u.get('raw', [0] * 19))
    return narc_replace(data, 0, bytes(sub))

def party_slots(rom, fl):
    sub = narc_subs(rom.read(f'/yamada/DataBase/db_party_{900+fl}.narc'))[0][0]
    return [struct.unpack_from('<IHHHHH', sub, i * 14)[2:4] for i in range(len(sub) // 14)]

# --- Subfile 1 = AI-Skill-Scripts pro Einheit (36-u16-Bloecke) ---
AI_HDR = 72; AI_BLK = 72
def ai_count(narc):
    subs = narc_subs(narc)[0]
    return (len(subs[1]) - AI_HDR) // AI_BLK if len(subs) > 1 else 0
def set_ai(narc, idx, ids):
    subs = narc_subs(narc)[0]; s1 = bytearray(subs[1]); off = AI_HDR + idx * AI_BLK
    hdr = struct.unpack_from('<H', s1, off)[0]
    ids = list(ids)[:35]; blk = [hdr] + ids + [0xFFFF] * (35 - len(ids))
    struct.pack_into('<36H', s1, off, *blk)
    return narc_replace(narc, 1, bytes(s1))

def terrain(rom, fl):
    return narc_subs(rom.read(f'/yamada/DataBase/db_dpos_{900+fl}.narc'))[0][2]

# ---------------------------------------------------------------- Pool/Stats
ARM9 = 0x101C52
POOL = [5,9,14,15,16,18,23,24,28,29,37,43,56,63,64,65,66,67,68,89,92,105,113,115,117,
        119,121,123,125,127,129,131,132,133,134,136,137,138,139,140,141,142,143,144,
        145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,
        164,165,166,167,168,182,183,184,186,187,188,189,196,197,198,199,206,207,208,
        209,216,217,218,219,226,227,228,229,236,237,238,239,240,241,242,243,244,245,
        246,247,248,249,250,251,252,253,254]
BIG = {148,149,150,163,164,165,166,167,168,237,252}
BLACK = {176,177,185,151}
MAX_UNIQUE = 25

def noncom_set(rompath):
    with open(rompath, 'rb') as f: rom = f.read()
    ns = set()
    for u in POOL:
        off = ARM9 + (u - 15) * 70
        if struct.unpack_from('<H', rom, off + 6)[0] == u and rom[off + 21] in (0, 4):
            ns.add(u)
    return ns

def sprite_ok(rom, u):
    off = ARM9 + (u - 15) * 70
    with open(rom.path, 'rb') as f: f.seek(off + 4); p = struct.unpack('<H', f.read(2))[0]
    return f'/kuro/nc_main/bat_main_nc{p:03d}.bin' in rom.by

def facing(gx, gy, pcx, pcy):
    dx, dy = pcx - (gx + 1), pcy - (gy + 1)
    return (0 if dx > 0 else 2) if abs(dx) >= abs(dy) else (3 if dy > 0 else 1)

# ---------------------------------------------------------------- Aktionen
def randomize(rom, fl, level, nmin, nmax, names, noncom):
    grid = terrain(rom, fl); ps = party_slots(rom, fl)
    pcx = sum(x for x, y in ps) / len(ps); pcy = sum(y for x, y in ps) / len(ps)
    blocked = set()
    for x, y in ps:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1): blocked.add((x - 1 + dx, y - 1 + dy))
    cells = [(x, y) for y in range(39) for x in range(39)
             if y * 39 + x < len(grid) and grid[y * 39 + x] == 10 and (x, y) not in blocked]
    pool = sorted(set(POOL) - BIG - BLACK - noncom)
    pool = [u for u in pool if sprite_ok(rom, u)]
    count = min(random.randint(nmin, nmax), len(cells), MAX_UNIQUE, len(pool))
    chars = random.sample(pool, count)
    lo, hi = max(1, level - 5), min(99, level + 5)
    units = []
    for i, (char, (gx, gy)) in enumerate(zip(chars, random.sample(cells, count))):
        units.append({'slot': 16 + i, 'active': 3, 'char': char, 'level': random.randint(lo, hi),
                      'x': gx + 1, 'y': gy + 1, 'dir': facing(gx, gy, pcx, pcy),
                      'raw': [0, 3, 100] + [0] * 16})
    rom.write(f'/yamada/DataBase/db_dpos_{900+fl}.narc', pack_units(rom, fl, units))
    print(f'  Etage {fl}: {count} Gegner Lv{lo}-{hi} gesetzt.')
    for u in units:
        print(f'    {names.get(u["char"],"?"):<14} Lv{u["level"]} @({u["x"]},{u["y"]})')

def set_points(rom, fl, pts):
    # db_result.inc (laengenneutral) + ARM9-Zwilling @0xF8998
    path = '/yamada/DataBase/db_result.inc'
    d = rom.read(path).decode('ascii'); import re
    for line in d.split('\r\n'):
        t = re.findall(r'-?\d+', line)
        if t and int(t[0]) == fl:
            old = line[:line.index('{')]
            m = list(re.finditer(r'-?\d+', line))
            s, e = m[1].start(), m[1].end()
            newline = line[:s] + str(pts).rjust(e - s)[:e - s] + line[e:]
            # laengenneutral: falls neue Zahl kuerzer -> mit Space, laenger -> Space wegnehmen
            newline = line[:s] + str(pts) + line[e:]
            diff = len(newline) - len(line)
            if diff > 0:  # kuerzen ueber folgende Spaces
                newline = newline.replace(', ', ',', diff)
            elif diff < 0:
                newline = newline[:s + len(str(pts))] + ' ' * (-diff) + newline[s + len(str(pts)):]
            d = d.replace(line, newline, 1)
            break
    if len(d) <= rom.fat[rom.by[path]][1] - rom.fat[rom.by[path]][0]:
        rom.write(path, d.encode('ascii'))
    # ARM9-Zwilling
    with open(rom.path, 'r+b') as f:
        base = 0xF8998; off = base + (fl - 1) * 68
        f.seek(off); nr = struct.unpack('<H', f.read(2))[0]
        if nr == fl:
            f.seek(off + 2); f.write(struct.pack('<H', pts))
    print(f'  Etage {fl}: {pts} Skillpoints (bei Sieg pro ueberlebendem Char).')

def skill_chaos(rom, fl, skill_names):
    """Allen Gegnern der Etage je 1-5 zufaellige Battle-Skills geben (Subfile 1)."""
    en = sorted((u for u in floor_units(rom, fl) if u['slot'] >= 16),
                key=lambda u: u['slot'])
    if not en:
        print('  Keine Gegner - erst randomisieren.'); return
    pool = [sid for sid, nm in skill_names.items() if nm.strip() and 1 <= sid <= 116]
    narc = rom.read(f'/yamada/DataBase/db_dpos_{900+fl}.narc')
    if ai_count(narc) < len(en):
        print('  AI-Bloecke passen nicht - erst neu randomisieren.'); return
    for i in range(len(en)):
        n = random.randint(1, 5)
        narc = set_ai(narc, i, random.sample(pool, min(n, len(pool))))
    rom.write(f'/yamada/DataBase/db_dpos_{900+fl}.narc', narc)
    print(f'  SKILL-CHAOS: {len(en)} Gegner mit je 1-5 Zufalls-Skills.')

# ---------------------------------------------------------------- Menue
def menu():
    path = find_rom()
    if not path:
        print('ROM nicht gefunden. Bitte oben ROM_PATH setzen.'); return
    print('ROM:', path)
    rom = Rom(path)
    names = bgsm(rom.read('/yamada/ScrDat/s_name.bin'))
    sknames = bgsm(rom.read('/yamada/DataBase/db_skill_name.bin'))
    noncom = noncom_set(path)
    while True:
        print('\n=== Bleach 3P Mobil-Editor ===')
        print(' 1) Etage anzeigen')
        print(' 2) Etage randomisieren')
        print(' 3) Skillpoints einer Etage setzen')
        print(' 4) GOD-MODE Etage (Lv91-99)')
        print(' 5) Skill-Chaos (Gegner je 1-5 Zufalls-Skills)')
        print(' 0) Beenden')
        c = input('Wahl: ').strip()
        try:
            if c == '1':
                fl = int(input('Etage (1-30): '))
                for u in floor_units(rom, fl):
                    if u['slot'] >= 16:
                        print(f'  {names.get(u["char"],"?"):<14} Lv{u["level"]} @({u["x"]},{u["y"]})')
            elif c == '2':
                fl = int(input('Etage (1-30): ')); lv = int(input('Ziel-Level: '))
                mn = int(input('Gegner min: ')); mx = int(input('Gegner max: '))
                randomize(rom, fl, lv, mn, mx, names, noncom)
            elif c == '3':
                fl = int(input('Etage (1-30): ')); p = int(input('Skillpoints: '))
                set_points(rom, fl, p)
            elif c == '4':
                fl = int(input('Etage (1-30): '))
                randomize(rom, fl, 95, 8, 12, names, noncom)
                print('  (GOD-MODE = Lv91-99; Stats bleiben - fuer starke Stats den PC-Editor)')
            elif c == '5':
                fl = int(input('Etage (1-30): '))
                skill_chaos(rom, fl, sknames)
            elif c == '0':
                print('Fertig. ROM gespeichert:', path); break
        except Exception as e:
            print('  Fehler:', e)

if __name__ == '__main__':
    menu()
