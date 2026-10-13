# Bleach: The 3rd Phantom — RE-Toolkit & Mods

Werkzeuge, Doku und Mods zum NDS-Spiel *Bleach: The 3rd Phantom* (EU, YBTP).
Das **Hauptprojekt** (eigene Browser-Engine) liegt in
[YAH-Datyx/Bleach3P-](https://github.com/YAH-Datyx/Bleach3P-). Die Funde aus
diesem Repo stehen dort gesammelt in `docs/wissen-re-toolkit.md`, die Tools
unter `tools/s2/`.

> **Rechtlich:** keine ROM-Daten und keine extrahierten Assets im Repo. Die
> eigene ROM gehört nach `rom/Bleach3rdPhantom.nds` (gitignored).

## Ordner

```
apps/            Quellcode der Artifacts (Seelenturm, Taschenkonsole)   → apps/README.md
docs/            Doku, Inhaltsverzeichnis                                → docs/README.md
mods/            eigene Mods als JSON (Fix-Mod, Beispiel)
tests/           pytest (synthetisch; ROM-Tests laufen nur mit entpackter ROM)
tools/scripts/   Spieldaten, Huffman, ROM-Build, Mod-Build (Python, ndspy)
tools/re/        Reverse Engineering: DB-Tabellen, NCER/NANR, CPK, Ghidra
tools/*.sh       ältere Shell-Helfer (ndstool-Weg)

gitignored, aus der eigenen ROM erzeugt:
rom/ unpacked/ unpacked-decomp/ gamedata/ build/
```

## Schnellstart

```bash
pip install ndspy pillow capstone pytest
python3 tools/scripts/unpack_rom.py rom/Bleach3rdPhantom.nds unpacked
python3 tools/scripts/decompress.py                    # Huffman → unpacked-decomp/
python3 tools/scripts/gamedata.py export               # Spieldaten → gamedata/*.json
python3 tools/scripts/gamedata.py validate             # bekannte Crash-Ursachen
python3 tools/scripts/make_mod.py mods/fix-partner-conflicts.json   # → build/*.nds + .xdelta
python3 -m pytest tests/
```

## Wichtigste Funde (Details in `docs/`)
- Das Spiel liest **keine `.inc`-Dateien**, nur die Binärtabellen in arm9 ([db-tables.md](docs/db-tables.md)).
- Spawn: nur Welle 0 beim Start, höchstens 32 Aktoren, nur 64 dpos-Slots ([spawn-logic.md](docs/spawn-logic.md)).
- Partner = Gegner auf derselben Etage führt zum Crash. Etage 7 ist noch offen.
- Huffman-Encoder, NCER/NANR- und CPK-Writer: alle Dateien der ROM round-trip-getestet ([file-formats.md](docs/file-formats.md)).
