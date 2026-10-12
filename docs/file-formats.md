# Dateiformate — was sich zerlegen, ändern und analysieren lässt

Stand: Scan der ROM YBTP mit `tools/re/classify.py`. Die vollständige Tabelle
aller Dateigruppen steht in [`file-formats-scan.md`](file-formats-scan.md).

**6126 Dateien, Überblick:**
- 2756 Huffman-komprimiert. **Alle** dekomprimieren exakt, und **jede** enthält ein NARC.
- 1639 ADX/AHX (Audio)
- 735 NARC
- ~700 lose Nitro-Grafik
- 107 CPK

## Kompression

| Typ | Wo | Status |
|---|---|---|
| Huffman 8-bit (`0x28`) / 4-bit (`0x24`) | fast alle `yamada/`, `kuro/`, `kow/`-`.bin` | ✅ `decompress.py`. Der Fehler bei der Kinderknoten-Adresse ist behoben, 2756/2756 korrekt |
| LZ10/LZ11 | kaum | ✅ ndspy |
| Huffman-**Encoder** | Zurückschreiben geänderter Assets | ✅ `compress.py`. Alle 2756 Dateien round-trip-getestet (neu komprimiert → identisch entpackt) |

```bash
python3 tools/scripts/decompress.py      # unpacked/data → unpacked-decomp/data (gitignored)
# … Dateien in unpacked-decomp/ bearbeiten …
python3 tools/scripts/recompress.py      # geänderte Dateien neu komprimieren → unpacked/data
python3 tools/scripts/build_rom.py       # rom/ + unpacked/ → build/Bleach3rdPhantom.patched.nds
```

`build_rom.py` braucht kein ndstool und übernimmt nur Dateien, die sich vom
Original unterscheiden. Getestet: Ohne Änderungen ist die gebaute ROM
inhaltlich identisch, und eine geänderte Map-Grafik kommt korrekt in der ROM an.

## Inhalte nach Bereich

| Pfad | Inhalt (nach Dekompression) | Zerlegbar/änderbar | Tool |
|---|---|---|---|
| `yamada/DataBase/*.narc`, arm9-Tabellen | Spieldaten | ✅ lesen + schreiben | `gamedata.py`, `db-tables.md` |
| `yamada/DataBase/*.inc` | Quell-CSVs der Entwickler (C-Initialisierer) | ✅ Layout-Vorlage | — |
| `yamada/FMap/MAP###.bin` | Map-Grafik: NCGR+NCLR+NSCR (+ Sprite NCER/NANR) | ✅ → PNG | `tools/re/nitro2png.py` |
| `yamada/NCface/nc_#####.bin` (600) | Gesichts-Porträts (NCGR+NCLR) | ✅ → PNG | nitro2png |
| `yamada/Status/`, `kuro/nc_main/`, `kuro/nc_sub/`, `kuro/ex_p/` | Status- und Kampfbilder | ✅ → PNG | nitro2png |
| `yamada/FPiece/` | Einheiten-Sprites auf der Map (NCER+NANR, animiert) | ⚠️ Tiles → PNG, Cells/Animation offen | nitro2png (Tiles), NitroPaint |
| `yamada/AdvBG/` | Adventure-Hintergründe (NARC mit BG) | ✅ → PNG | nitro2png |
| `oosawa/**.NCGR`, `evs_cp*.narc`, `sys_*.narc`, `chiba/` | Cutscenes, Menüs, Tutorials | ✅/⚠️ | nitro2png, NitroPaint/Tinke |
| `yamada/ScrDat/map####.bin`, `adv_[se]####.bin`, `main##.bin` | **Skripte**: NARC aus `BSVE` (Bytecode + Offset-Tabelle) und `BGSM` (Nachrichten + Offset-Tabelle) | ⚠️ Container verstanden, Opcodes und Zeichentabelle offen | — |
| `*_fre.*` | französische Variante derselben Datei (EU-ROM, EnFr) | wie oben | — |
| `yamada/System/sys_win_moji###`, NFTR ×3 | Schriften und Glyphen, nötig für die Text-Kodierung | ⚠️ | Tinke |
| `kuro/c#/c#.cpk`, `FPiece.cpk`, `CPanel/*.cpk` | CRI-CPK-Archive (89 Charakter-Pakete) | ⚠️ Format bekannt (CRI), Tool fehlt | z. B. CriPakTools |
| `kuro/macro/M_#ST_#_TBL.bin` | Rohtabellen (Kampf-Makros?) | ❓ | — |
| `sound/*.adx`, `sound/voice/**.ahx` | CRI ADX/AHX Musik und Stimmen | ✅ dekodierbar (vgmstream) | vgmstream |
| `kow/effects/` | Effekt-Grafiken | ✅ → PNG | nitro2png |

## Folgerungen für die eigene Engine / App

- **Daten:** Tabellen und Floors sind fertig (JSON).
- **Grafik:** Maps, Porträts und BGs lassen sich jetzt automatisch nach PNG exportieren.
  Sprite-Animationen (NCER/NANR) fehlen noch.
- **Audio:** ADX/AHX ist Standard und lässt sich mit vgmstream nach WAV/OGG wandeln.
- **Skripte und Text:** größter offener Block. Nötig sind die BSVE-Opcodes und die
  BGSM-Zeichentabelle (über die Schrift).
- **Zurückschreiben in die ROM:** geht für Daten, Grafiken und jede andere
  Datei (`recompress.py` + `build_rom.py`).

Exportierte Assets gehören den Rechteinhabern und bleiben lokal in `build/`
bzw. `unpacked-decomp/` (beide gitignored).
