# Bekannte Character-IDs

In-game-Tests haben folgende Char-IDs identifiziert. Pool zum sicheren Nutzen für Mods.

## Visuell bestätigte Charaktere

### Named (echte Charaktere, nutzbar als Enemy wenn nicht rekrutiert)

| ID | Name | Klasse | Quelle |
|----|------|--------|--------|
| 14 | Yamamoto (wahrscheinlich) | Power | Floor 30, Lv 85, ~5200 HP |
| 21, 23, 25, 27, 29 | Squad 11 (Kenpachi-Themed) | Power | Floor 14/30 Partner |
| 125 | D-Roy Linker | Speed | Floor 30 Slot 23, Lv 78 |
| 141 | Ikkaku Madarame (vermutet) | Power | Floor 14 Boss-Slot |
| 144 | Kusaka | Speed | **Recruited → wird Ally** |
| 181 | Ukitake | Tech | Floor 9 Test, Lv 88 Enemy |
| 199 | Kaien | Power | Floor 9 Test, Lv 88 Enemy |
| 200 | Fujimaru Kudō | Speed | 3rd Phantom MC |
| 208 | Hisagi | Speed | Floor 9 Test, HP 1501 |
| 219 | Urahara (Past) | Tech | Floor 9 Test |
| 220 | Fujimaru-Variante | — | (unsichtbar bei Recruit) |
| 226 | Urahara (current) | Tech | Floor 9 Test, HP 1276 |
| 230 | Matsuri (vermutlich) | Power | Recruited |
| 240 | Shiyo Kudō | Speed | 3rd Phantom MC Schwester |
| 245 | Kon | Tech | Plüsch-Löwe |
| 250 | Drunk Reaper (Kyoraku?) | Power | Lv 88 Test |
| 254 | Ichigo Kurosaki | All | Bleach MC |

### Hollow / Enemy-Only (nie rekrutierbar — beste Wahl für Tower-Mods)

| ID | Name | Klasse | Hinweis |
|----|------|--------|---------|
| 154 | Hell Mantis | Tech | Hollow-Template |
| 155 | Hell Mantis | Power | Hollow-Template |
| 156 | Sky Rift | NonCom | Portal/Effekt |
| 157 | Frog Head | Tech | HP 1528 @ Lv 88 |
| 158 | Frog Head | Power | HP 1545 @ Lv 88 |
| 159 | Frog Head (variant) | — | (Floor 12 native) |
| 185 | Hell Mantis | Power | Hollow-Template |
| 188 | Matsuri-Variante (namenlos) | Power | HP 1067 @ Lv 88 |
| 208 | Hisagi (variant) | Speed | — |
| 213 | Evil Eater | Speed | HP 3501 @ Lv 88, tanky |
| 235 | Matsuri-Variante (namenlos) | Speed | HP 1067 @ Lv 88 |

### Enemy-Variants von Bleach-Hauptcharakteren (durch Session 3 entdeckt)

Trotz dass der Spieler diese Charaktere rekrutiert hat, gibt es spezifische ID-Varianten die als Lv-88-ENEMY erscheinen statt Ally — wahrscheinlich anderer Sprite-Slot mit Enemy-Flag:

| ID | Name | Klasse | Hinweis |
|----|------|--------|---------|
| 181 | Ukitake (enemy variant) | Tech | Lv 88 Enemy |
| 197 | Hanataro (enemy variant) | NonCom | Healing Support |
| 199 | Kaien | Power | Lv 88 Enemy, HP 1493 |
| 211 | Orihime (enemy variant) | Tech | HP 997 |
| 219 | Urahara Past | Tech | HP 1276 |
| 226 | Urahara (current) | Tech | HP 1276 |
| 228 | Rukia (enemy variant) | Speed | HP 1025 |
| 247 | Shinji (Vizard) | Tech | HP 1597 |
| 248 | Hiyori (Vizard) | Speed | HP 1223 |
| 252 | Giant Entity | All | HP 5752 — Boss-tier! |

### Aizen-Boss-Variants

Mehrere Aizen-Enemy-IDs entdeckt:
- Eine ID gibt Aizen Tech Lv 88 normal (HP ~1122)
- Eine ID gibt **Boss-Aizen All-Klasse** Lv 88, **HP 9714** — extrem tanky, wahrscheinlich Hueco-Mundo-Endform

### Andere named Enemies (Session 3 IDs noch nicht alle einzeln gemappt)
- Don Kan'onji (TV Geisterjäger, Tech, HP 1502)
- Yoruichi (Speed enemy variant + All-Class-Variant)
- Konoka (NonCom, SP Recovery)
- Momo (Speed)
- Nemu (Tech)
- Jidanbo (Power, HP 3057 — tank)
- Izuru (Tech enemy variant)
- Chad (Power)
- Uryu (Speed enemy variant)
- Kukaku (named enemy)
- Rangiku (Tech enemy variant)
- "M. Soul Reaper" (Male Generic Shinigami)
- "Female Spirit" (NonCom generic)
- Matsuri Kudo enemy variant (Power, HP 1164)

## Char-Klassen (aus In-Game UI)

| Klasse | Bedeutung |
|---|---|
| Power | hohe ATK, mittlere DEF |
| Speed | hohe SPD/EVA, niedrige DEF |
| Tech | hoher MAG, durchschnittlich sonst |
| NonCom | kein Combat-Char (Portale, Spawn-Points) |
| All | All-rounder (Ichigo) |

## Stat-Skalierung

Stats werden zur Laufzeit berechnet:
- Base-Stats aus `arm9.bin[0xfd882]` (siehe `arm9-stats.md`)
- Skaliert mit Level (`displayed = base + (level - 1) × growth`)
- Mod auf Base wirkt auf ALLE Vorkommen des Chars

Soi Fon-Beispiel: Lv 28, displayed HP 533. Wenn Base-Tabelle alle IDs mit HP=9876 patched werden, zeigt Soi Fon 9976 (9876 + 100 growth) → identifiziert ihre ID im Range 128-143 via Binary Search.

## Bekannt kaputte / instabile IDs

Diese verursachen Crash beim Spawnen (vermutlich Filler-Slots ohne komplette Sprite/Animation/Stats):

`30, 90, 100, 110, 145, 146, 147, 150, 170, 175, 193, 195`

Einer davon ist der „rothaarige kleine Junge" der nur einmal in der Story als Filler auftaucht und keine Animationen hat.

## Unsichtbar / vom Spiel gefiltert

| ID | Verhalten |
|----|-----------|
| 220 | Slot wird gesetzt aber Char ist nicht sichtbar auf der Map (vermutlich Fujimaru-Recruit-Filter) |
| 232, 241 | Keine sichtbare Änderung |

## Identifikations-Workflow (Binary Search)

Um eine unbekannte Char-ID zu finden:

1. **Mass-Patch** alle aktiven IDs der Stat-Tabelle mit HP-Marker (z.B. 9876)
2. **In-Game**: Char im Spiel anschauen — wenn HP `9876 + level_offset` zeigt, ist Char in der Tabelle
3. **Binary Search**: Halbiere die Patch-Range bis genaue ID gefunden

## Recruit-Aware Logic (Wichtig!)

Wenn der Spieler einen char_id rekrutiert hat (im Save-Game), wird dieser char_id beim Enemy-Spawn **automatisch zum Ally** mit dem Save-Level — egal welches `team`-Feld gesetzt wird.

**Konsequenz für Mods:** Um echte Tower-Enemies zu bauen, nutze Char-IDs die der Spieler **nicht** rekrutiert hat. Hollow-IDs (154-159, 185, 188, 208, 213, 235) sind die sichersten Choices.

## Pool-Empfehlungen für Floor-Mods

**Garantiert Enemy (Hollow-only, kein Recruit-Konflikt):**
```python
HOLLOW_POOL = [154, 155, 156, 185,           # Hell Mantis & Sky Rift
               157, 158, 159,                 # Frog Head Varianten
               188, 208, 213, 235]            # weitere Hollow-Types
```

**Named Enemies (mit Risiko Ally-Konvertierung wenn rekrutiert):**
```python
NAMED_POOL = [181, 199, 213, 219, 226]       # Ukitake, Kaien, Evil Eater,
                                              # Urahara Past, Urahara
```

**Vollständiger Floor-9-Pool (14 IDs, alle bestätigt):**
```python
ALL_TESTED = [154, 155, 156, 157, 158, 159,
              181, 185, 188, 199, 208, 213,
              219, 226, 235]
```
