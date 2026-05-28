# Bekannte Character-IDs

In-game-Tests haben folgende Char-IDs identifiziert. Pool zum sicheren Nutzen für Mods.

## Visuell bestätigte Charaktere

| ID | Name | Hinweis |
|----|------|---------|
| 14 | Yamamoto (wahrscheinlich) | Floor 30, Lv 85, ~5200 HP — Captain-Commander |
| 21, 23, 25, 27, 29 | Squad 11 (Kenpachi-Themed Variants) | Partner-Rolle auf Floor 14/30 |
| 125 | D-Roy Linker | Floor 30 Slot 23, Lv 78 (Arrancar) |
| 141 | Ikkaku Madarame (vermutet) | Floor 14 Boss-Slot |
| 154, 155, 185 | Hell Mantis (Hollow-Templates) | Power/Tech-Varianten |
| 156 | Sky Rift | „NonCom" — Portal-/Effekt-Entity, kein echter Char |
| 200 | Fujimaru Kudō | Hauptcharakter (3rd Phantom MC, blond) |
| 220 | Fujimaru-Variante | weitere Fujimaru-Form |
| 230 | Unbekannte blonde Schülerin | wahrscheinlich Matsuri-ähnlich |
| 240 | Shiyo Kudō | Fujimarus Schwester |
| 245 | Kon | Plüsch-Löwe (Maskottchen) |
| 250 | Drunk Reaper | wahrscheinlich Shunsui Kyoraku |
| 254 | Ichigo Kurosaki | Hauptcharakter Bleach |

## Char-Klassen (aus In-Game UI)

| Klasse | Bedeutung |
|---|---|
| Power | hohe ATK, mittlere DEF |
| Speed | hohe SPD/EVA, niedrige DEF |
| Tech | hoher MAG, durchschnittlich sonst |
| NonCom | kein Combat-Char (Portale, Spawn-Points) |

## Stat-Skalierung

Stats werden zur Laufzeit berechnet:
- Base-Stats aus `arm9.bin[0xfd882]` (siehe `arm9-stats.md`)
- Skaliert mit Level (`displayed = base + (level - 1) × growth`)
- Mod auf Base wirkt auf ALLE Vorkommen des Chars

Soi Fon-Beispiel: Lv 28, displayed HP 533. Wenn Base-Tabelle alle IDs mit HP=9876 patched werden, zeigt Soi Fon 9976 (9876 + 100 growth) → identifiziert ihre ID im Range 128-143 via Binary Search.

## Bekannt kaputte / instabile IDs

Diese verursachen Crash beim Spawnen:

- **100, 145, 146, 147, 150, 175, 195** — vermutete „Filler"-IDs ohne komplette Daten

Einer davon ist der „rothaarige kleine Junge" der nur einmal in der Story als Filler auftaucht und keine Animationen hat.

## Identifikations-Workflow (Binary Search)

Um eine unbekannte Char-ID zu finden:

1. **Mass-Patch** alle aktiven IDs der Stat-Tabelle mit HP-Marker (z.B. 9876)
2. **In-Game**: Char im Spiel anschauen — wenn HP `9876 + level_offset` zeigt, ist Char in der Tabelle
3. **Binary Search**: Halbiere die Patch-Range bis genaue ID gefunden

Beispiel-Skript siehe `tools/scripts/find_char_id.py` (TODO falls noch nicht erstellt).

## Pool-Empfehlungen für Floor-Mods

**Sicher (visuell bestätigt, kein Crash):**
- 21, 23, 25, 27, 29 (Squad 11) — aber NUR als Enemy verwenden falls nicht gleichzeitig Partner!
- 130-143 außer 141 (gebuffter Bereich, mehrere Bleach-Chars)
- 200, 220, 230, 240, 245, 250, 254 (Haupt-/Recruitable-Chars)
- 216, 217, 218 (Floor 14 Original-Bosse)

**Erkundet auf Floor 30 (Endgame-Tower):**
- 5, 14, 43, 113, 115, 125, 129, 132, 133, 141 (regulär)
- 154, 155, 156, 185 (Hollow-Templates, nicht-named)
- 253, 254 (Hauptcharaktere)
