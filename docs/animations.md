# Animationen: finden, exportieren, umbauen, neu hinzufügen

Werkzeuge: `tools/re/anim.py` (Arbeitsablauf), `tools/re/nitro_anim.py`
(NCER/NANR lesen und schreiben), `tools/re/cpk.py` (Charakter-Pakete).

## Wo die Animationen liegen

| Ort | Inhalt | Anzahl |
|---|---|---|
| `kuro/c###/c###.cpk` (+ `c###b.cpk`) | **Kampf-Animationen pro Charakter.** Jeder CPK-Eintrag (ID) ist eine Aktion mit 1 Sequenz und 1–30 Frames. Paletten liegen als eigene Einträge ab ID 10000 | 1584 Animationen in 89+ Paketen |
| `yamada/FPiece/FPiece_2d_###n/b.bin` | Einheiten auf der Taktik-Map, z. B. `wait_rd/ru/lu/ld` = Warten in 4 Richtungen | 129 |
| `kow/effects/*.bin`, `tactics.bin` | Kampf- und Skill-Effekte | ~140 |
| `yamada/FMap/MAP###.bin` | animierte Map-Teile (`CellAnime0…`) | 33 |
| `yamada/FEffect/`, `yamada/FSkillB/` | Feld- und Skill-Effekte | 31 |
| `oosawa/*/*_spr.narc` | Cutscene-Sprites | ~13 |
| UI (`sys_*`, `kuro/g/`, `chiba/`, …) | Cursor, Icons, Anzeigen | ~30 |

`python3 tools/re/anim.py list` listet alle Animationen mit ihren Sequenznamen.

Welche CPK-ID zu welcher Aktion gehört (Idle, Angriff, Treffer …), steht
nicht in den Dateien. Ermitteln lässt sich das über die Code-Stelle, die die
CPK-IDs lädt, oder durch Testen im Emulator.

## Arbeitsablauf

```bash
python3 tools/scripts/decompress.py                                   # einmalig
python3 tools/re/anim.py export yamada/FPiece/FPiece_2d_001n.bin build/anim/fp001
python3 tools/re/anim.py export 'kuro/c001/c001.cpk#3'           build/anim/c001_3
# … bearbeiten (siehe unten) …
python3 tools/re/anim.py import build/anim/fp001
python3 tools/scripts/recompress.py
python3 tools/scripts/build_rom.py
```

Arbeitsordner:

| Datei | Zweck |
|---|---|
| `nanr.json` | **Sequenzen**: `frames[]` mit `cell` (Zellnummer) und `duration` (1/60 s); dazu `loop_start` und `play_mode`. Frames umordnen, löschen und kopieren geht ebenso wie neue Sequenzen anhängen |
| `ncer.json` | **Zellen**: `oam[]` mit `x`, `y` (relativ zum Ursprung), `w`/`h` (8–64, nur DS-Größen), `tile`, `palette`, `hflip`/`vflip`. Neue Zellen anhängen geht |
| `tiles.png` | Tile-Grafik als **indiziertes PNG**. Pixelwert = Farbnummer, bei 4 Bit 0–15, 0 = transparent |
| `source.json` | Herkunft; `tile_count` erhöhen (und `tiles.png` vergrößern) hängt neue Tiles an |
| `cells/`, `preview/*.gif` | nur zur Ansicht |

Felder mit `_` (z. B. `_raw`, `_data_off`) sind Originalbytes für das exakte
Zurückschreiben. Bei neuen Einträgen weglassen.

## Was verifiziert ist

- Alle **558 NCER und 558 NANR** der ROM: Binär → JSON → Binär ist byte-identisch.
- Alle **107 CPKs** (3081 Einträge): Die eingebaute CRILAYLA-Kompression hat eine
  genullte Signatur. Entpacken ergibt exakt `ExtractSize`, unverändertes Neubauen
  ist byte-identisch.
- Umbau-Tests: Dauer ändern, Frames umkehren, neue Sequenz und neue Zelle
  anlegen, Tiles anhängen. Alles wird korrekt zurückgelesen. Das gilt auch für
  geänderte Einträge in CPKs.
- **Nicht getestet ist das Verhalten im laufenden Spiel.** Erst im Emulator prüfen.

## Grenzen und Hinweise für eigene Inhalte

- **Farben:** Eine 4-Bit-Grafik hat 16 Farben pro Palette. Neue Pixel müssen
  vorhandene Farbnummern benutzen, oder die Palette (NCLR) wird mit angepasst.
- **VRAM-Transfer** (z. B. FPiece): Jede Zelle lädt einen eigenen Tile-Block
  (`ncer.json → vram.cells = [offset, size]`). Eine neue Zelle braucht einen
  eigenen Eintrag, und `size` darf `vram.max_size` nicht überschreiten.
- **Speicher:** Mehr Tiles oder größere Zellen brauchen mehr Sprite-VRAM.
  Deutlich größere Animationen können im Spiel Grafikfehler erzeugen.
- **CPK:** Geänderte Einträge werden unkomprimiert abgelegt
  (FileSize = ExtractSize). Die Paketgröße wächst dabei leicht.
- **Neue Aktionen** (neue CPK-IDs) brauchen zusätzlich Code oder Daten, die sie
  aufrufen. Am einfachsten ist es, eine vorhandene Aktion umzubauen.
- Für eigene Figuren eigene Grafiken zeichnen. Extrahierte Original-Assets
  bleiben lokal (`build/`, `unpacked-decomp/` sind gitignored).
