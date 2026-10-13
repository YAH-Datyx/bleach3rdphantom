"""Bleach: The 3rd Phantom (EU) - NDS ROM filesystem library.

Liest Header, FNT (Dateinamen) und FAT (Offsets) der ROM und kann
einzelne Dateien extrahieren oder (bei gleicher Groesse) in-place patchen.
"""
import struct, os

DEFAULT_ROM = r"C:\Users\danie\OneDrive - Technische Hochschule Rosenheim\Desktop\Bleach3P_RE\Bleach3P modded.nds"


def read_header(f):
    f.seek(0)
    h = f.read(0x200)
    return {
        'title':    h[0:12].decode('ascii', 'replace').rstrip('\0'),
        'gamecode': h[12:16].decode('ascii', 'replace'),
        'fnt_off':  struct.unpack_from('<I', h, 0x40)[0],
        'fnt_size': struct.unpack_from('<I', h, 0x44)[0],
        'fat_off':  struct.unpack_from('<I', h, 0x48)[0],
        'fat_size': struct.unpack_from('<I', h, 0x4C)[0],
        'arm9_rom': struct.unpack_from('<I', h, 0x20)[0],
        'arm9_size': struct.unpack_from('<I', h, 0x2C)[0],
    }


def parse_fnt(f, fnt_off, fnt_size):
    f.seek(fnt_off)
    fnt = f.read(fnt_size)
    files = {}

    def walk(dir_id, path):
        sub_off, first_file = struct.unpack_from('<IH', fnt, (dir_id & 0xFFF) * 8)
        pos, fid = sub_off, first_file
        while True:
            ln = fnt[pos]; pos += 1
            if ln == 0:
                break
            name = fnt[pos:pos + (ln & 0x7F)].decode('ascii', 'replace')
            pos += ln & 0x7F
            if ln & 0x80:
                sub_id = struct.unpack_from('<H', fnt, pos)[0]; pos += 2
                walk(sub_id, path + name + '/')
            else:
                files[fid] = path + name
                fid += 1
    walk(0xF000, '/')
    return files


class RomFS:
    def __init__(self, rom_path=DEFAULT_ROM):
        self.rom_path = rom_path
        with open(rom_path, 'rb') as f:
            self.hdr = read_header(f)
            self.files = parse_fnt(f, self.hdr['fnt_off'], self.hdr['fnt_size'])
            f.seek(self.hdr['fat_off'])
            data = f.read(self.hdr['fat_size'])
            self.fat = [struct.unpack_from('<II', data, i * 8)
                        for i in range(self.hdr['fat_size'] // 8)]
        self.by_path = {p: fid for fid, p in self.files.items()}
        # Freien ROM-Platz fuer groessere Dateien (Relocation): hinter dem
        # hoechsten Datei-Ende liegt ~7 MB 0xFF-Padding bis zum ROM-Ende.
        self._rom_size = os.path.getsize(rom_path)
        self._free_ptr = (max(e for _, e in self.fat) + 3) & ~3
        self._reloc = {}            # fid -> (offset, kapazitaet) bereits umgezogen

    def read(self, path):
        fid = self.by_path[path]
        start, end = self.fat[fid]
        with open(self.rom_path, 'rb') as f:
            f.seek(start)
            return f.read(end - start)

    def _alloc(self, fid, size):
        """Freien ROM-Bereich fuer eine zu grosse Datei reservieren
        (pro fid wiederverwendet, solange die Groesse reinpasst)."""
        off, cap = self._reloc.get(fid, (None, 0))
        if off is None or size > cap:
            off = self._free_ptr
            self._free_ptr = (off + size + 3) & ~3
            if self._free_ptr > self._rom_size:
                raise ValueError('Kein freier ROM-Platz mehr fuer Relocation')
            self._reloc[fid] = (off, size)
        return off

    def write(self, path, data, out_rom=None):
        """Datei in der ROM ersetzen. Passt sie in ihren Original-Slot, wird
        in-place geschrieben (kleiner -> Rest genullt, FAT-Ende angepasst).
        Ist sie GROESSER, wird sie in den freien ROM-Platz am Ende umgezogen
        und ihr FAT-Eintrag (Start+Ende) umgebogen - so lassen sich z. B.
        groessere Donor-Maps auf beliebige Etagen legen.
        out_rom: Pfad fuer gepatchte Kopie (None = Original ueberschreiben)."""
        fid = self.by_path[path]
        start, end = self.fat[fid]
        orig_size = end - start
        target = out_rom or self.rom_path
        if out_rom and not os.path.exists(out_rom):
            import shutil
            shutil.copyfile(self.rom_path, out_rom)
        fat_ent = self.hdr['fat_off'] + fid * 8
        if len(data) <= orig_size:
            with open(target, 'r+b') as f:
                f.seek(start)
                f.write(data.ljust(orig_size, b'\0'))
                if len(data) != orig_size:
                    f.seek(fat_ent + 4)
                    f.write(struct.pack('<I', start + len(data)))
            return target
        # Relocation: Datei passt nicht in ihren Slot -> in freien Platz legen
        new_start = self._alloc(fid, len(data))
        new_end = new_start + len(data)
        with open(target, 'r+b') as f:
            f.seek(new_start)
            f.write(data)
            f.seek(fat_ent)
            f.write(struct.pack('<II', new_start, new_end))
            # Header "used ROM size" @0x80 nachziehen, falls noetig
            f.seek(0x80)
            used = struct.unpack('<I', f.read(4))[0]
            if new_end > used:
                f.seek(0x80)
                f.write(struct.pack('<I', new_end))
        # In-Memory-FAT nur beim In-Place-Ziel (Original) mitfuehren, damit
        # self.read weiter stimmt; bei Kopie bleibt das Modell am Original.
        if out_rom is None:
            self.fat[fid] = (new_start, new_end)
        return target
