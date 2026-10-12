# Roadmap: vom ROM-Hack zur eigenen App

Ziel: *The 3rd Phantom* als eigenständige App spielen, mit eigenen Inhalten
erweitern und mit anderen Spielen bzw. Projekten kombinieren.

## Ehrliche Einordnung

„Das gesamte Spiel reverse-engineeren“ ist kein einzelner Schritt, sondern
ein Projekt über viele Monate. Bisher kennen wir die Datentabellen (Stats,
Tower, Floor-Gegner und -Partner). Diese Teile fehlen noch:
Kampfformeln, KI, Map-Format, Grafik- und Animationsformate, Story-Skript und
Menülogik. Dafür braucht man die ROM lokal plus Ghidra und einen Debugger
(siehe `romhack-workflow.md`). Ohne ROM lässt sich nichts davon analysieren.

Drei Wege, sortiert nach Aufwand:

### A) Sofort: gemoddetes Original als App (Tage)

1. Mods als JSON in `mods/` schreiben → `gamedata.py apply` → `repack.sh`
2. Die gepatchte `.nds` in einem DS-Emulator für Android, iOS oder PC
   spielen (z. B. melonDS, DraStic oder DeSmuME).

Ergebnis: echte App auf dem Handy mit deinen Änderungen. Möglich sind aber nur
Änderungen innerhalb der Grenzen der Original-Engine, zum Beispiel ~13–24
Gegner pro Floor oder keine neuen Slots.

### B) Ziel: eigene Engine, die die Original-Daten liest (Monate)

Das Prinzip kennt man von OpenMW (Morrowind), OpenRCT2 und ScummVM. Die
Spiellogik wird **neu geschrieben**. Grafik, Sound und Daten werden zur
Laufzeit aus der ROM geladen, die der Spieler selbst mitbringt. Der Code
gehört dir und lässt sich frei erweitern. Inhalte aus anderen Spielen landen
über Importer im selben JSON-Format.

Empfohlener Stack: **Godot 4**. Damit gibt es einen Export für Android, iOS,
Windows, Linux und Web, Tilemaps und Grid-Logik sind eingebaut, und Godot
liest JSON nativ.

```
ROM (vom Nutzer) ──► Extraktor (Python, dieses Repo) ──► gamedata/ (JSON + PNG + OGG)
                                                            │
                         mods/*.json, andere Spiele ──► Merge│(gamedata.py apply-Logik)
                                                            ▼
                                                   Godot-Engine (eigener Code)
```

| Phase | Inhalt | Status |
|---|---|---|
| B1 | Datenlayer: Stats, Tower, Floors → JSON, Mod-Merge | ✅ `gamedata.py` |
| B2 | Item- und Skill-Tabellen (Arrays im Stat-Struct + Namen/Effekte finden) | offen |
| B3 | Grafik: NCGR/NCLR/NCER/NANR → PNG/Spritesheets (ndspy, Tinke als Referenz) | offen |
| B4 | Maps: Format hinter `map_id` entschlüsseln (Grid, Höhen, Hindernisse) | offen |
| B5 | Sound: SDAT → OGG (ndspy.soundArchive) | offen |
| B6 | Kampfregeln: Schadensformel, Trefferchance, Bankai in Ghidra nachbauen | offen, größter RE-Block |
| B7 | Gegner-KI (`ai_mode`-Werte, Zielwahl) | offen |
| B8 | Text und Story-Skript (Encoding, Control-Codes, Script-Opcodes) | offen |
| B9 | Godot-Prototyp: Grid-Kampf mit B1-Daten und Platzhaltergrafik | offen, sofort startbar |

B9 lässt sich parallel zum RE beginnen. Der Prototyp spielt zuerst mit
Platzhaltergrafik und bekommt die Originalassets, sobald B3 und B4 stehen.

### C) Vollständige Decompilation (Jahre)

Bei einer „matching decomp“ (wie pokeemerald) wird der ARM9-Code zurück in C
übersetzt, das byte-identisch kompiliert. Das ist der flexibelste Weg, aber
mit Abstand der aufwendigste und nur mit einer Community realistisch. Für
„eigene Inhalte und mit anderen Spielen mergen“ ist Weg B der bessere
Kompromiss.

## Rechtliches (kurz, keine Rechtsberatung)

- Code und Mods aus diesem Repo und eine eigene Engine dürfen geteilt werden.
- ROM, extrahierte Grafiken, Sounds und Texte gehören Sega bzw. den
  Rechteinhabern. Deshalb lädt die Engine sie aus der ROM des Nutzers und
  liefert sie nicht mit.
- Eine App, die Originalassets enthält, ist nur für den privaten Gebrauch
  gedacht. Für eine Veröffentlichung braucht es eigene Grafiken und Figuren.
