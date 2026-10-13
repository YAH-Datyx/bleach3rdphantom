# Spielen im Emulator (Handy & PC) mit deinen Mods

Das ist die exakte Original-Engine. Unsere Tools ändern nur Daten und Assets
in der ROM.

## 1. Mod-ROM bauen

```bash
python3 tools/scripts/make_mod.py mods/fix-partner-conflicts.json mods/<deine-mods>.json
# optional mit geänderten Grafiken/Animationen:
python3 tools/scripts/make_mod.py mods/*.json --assets unpacked-decomp/data
```

Ergebnis in `build/`:

- `Bleach3rdPhantom.mod.nds`: fertige ROM
- `Bleach3rdPhantom.mod.xdelta`: kleiner Patch, nur die Unterschiede

Der Patch passt **nur auf genau die Basis-ROM**, gegen die er gebaut wurde.
Deren sha1 gibt das Skript aus.

Hinweis: Die gebaute ROM ist etwas kleiner als das Original, weil das
Füll-Padding am Ende entfällt. Emulatoren stört das nicht.

## 2. Patch anwenden (falls du nur die .xdelta überträgst)

- **Browser (Handy und PC):** Rom Patcher JS (marcrobledo.com/RomPatcher.js) → ROM + `.xdelta` wählen → Patch anwenden
- **Windows:** „xdelta UI“ oder Kommandozeile `xdelta3 -d -s original.nds patch.xdelta mod.nds`
- **Android:** UniPatcher

## 3. Emulator

| Gerät | Emulator | Hinweis |
|---|---|---|
| Android | **melonDS** (Android-Port) oder **DraStic** | DraStic ist sehr schnell, melonDS genauer |
| iPhone/iPad | **Delta** (App Store) | DS-Unterstützung eingebaut |
| Windows/Mac/Linux | **melonDS** (empfohlen) oder **DeSmuME** | |

## 4. Spielstand mitnehmen (direkt in den Tower)

Den Story-Modus nicht neu spielen, sondern den vorhandenen Spielstand verwenden:

- Der Spielstand gehört zum ROM-Namen: `Bleach3rdPhantom.mod.nds` ↔ `Bleach3rdPhantom.mod.sav`.
  Die alte Save-Datei also kopieren und passend umbenennen.
- melonDS nutzt `.sav` (rohe Daten). DeSmuME nutzt `.dsv` mit einem kleinen
  Anhang am Ende. Beide Emulatoren können über ihr Menü Saves im jeweils
  anderen Format importieren bzw. exportieren.
- **Savestates** (Schnellspeicher) sind an Emulator und Version gebunden. Für
  den Wechsel zwischen Geräten immer den normalen Spielstand nehmen.

## 5. Testen nach einem Mod

1. ROM laden (in DeSmuME: File → Close, dann File → Open, kein Reset).
2. Den geänderten Floor betreten und prüfen, ob alle Gegner erscheinen.
3. Crasht etwas, erst `python3 tools/scripts/gamedata.py validate` laufen lassen.
   Es meldet bekannte Ursachen (Partner = Gegner, Crash-IDs, mehr als 24 Gegner in Welle 0).

## Mitgelieferter Fix

`mods/fix-partner-conflicts.json` ersetzt drei Gegner, die gleichzeitig Partner
auf ihrem Floor waren (bekannte Crash-Ursache). Ersatz sind Hollow-Gegner auf
gleichem Level:

| Floor | Slot | vorher | nachher |
|---|---|---|---|
| 6 | 16 | 29 (Partner) | 213 Evil Eater |
| 16 | 16 | 18 (Partner) | 158 Frog Head (Power) |
| 20 | 20 | 23 (Partner) | 157 Frog Head (Tech) |

Der Absturz auf Floor 7 ist damit **nicht** behoben. Seine Ursache ist noch
offen (siehe `session-findings.md`).
