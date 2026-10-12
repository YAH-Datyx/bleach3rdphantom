# Offenes Datenformat (`gamedata.py`)

`tools/scripts/gamedata.py` übersetzt alle bisher reverse-engineerten Tabellen
zwischen ROM-Binärformat und JSON. Das ist die gemeinsame Basis für Mods, für
das Zusammenführen mit anderen Projekten und für eine spätere eigene Engine
(siehe [`app-roadmap.md`](app-roadmap.md)).

```bash
./tools/unpack.sh                                   # ROM → unpacked/
python3 tools/scripts/gamedata.py export            # unpacked/ → gamedata/*.json
python3 tools/scripts/gamedata.py import            # gamedata/*.json → unpacked/
python3 tools/scripts/gamedata.py apply mods/a.json mods/b.json   # Mods stapeln
python3 tools/scripts/gamedata.py validate          # bekannte Crash-Ursachen prüfen
./tools/repack.sh                                   # unpacked/ → build/*.nds + xdelta
```

`gamedata/` ist gitignored, weil es aus der ROM stammt. Committet werden nur
Mods (`mods/*.json`), denn die enthalten ausschließlich deine eigenen Änderungen.

## Exportierte Dateien

| Datei | Quelle | Inhalt |
|---|---|---|
| `characters.json` | `arm9.bin @ 0xfd882` | Story-Stats, 70 Byte/Eintrag (siehe `arm9-stats.md`) |
| `characters_vs.json` | `arm9.bin @ 0xffc56` | VS-Stats; endet am ersten Eintrag mit `id != index+1` |
| `tower.json` | `arm9.bin @ 0xf3b58` | 30 Floors: `floor`, `map_id`, `floor_echo` |
| `floors/floor_XX.json` | `db_dpos_9XX.narc` + `db_party_9XX.narc` | `enemies[]` (54 B) + `partners[]` (14 B) |

Jeder Eintrag enthält die benannten Felder **und** `_raw` (Hex aller Bytes).
Beim Import wird `_raw` als Basis genommen, die benannten Felder werden darüber
geschrieben. Noch unbekannte Bytes bleiben also unverändert, und
`export → import` ist byte-identisch (das stellt `tests/test_gamedata.py` sicher).

Felder pro Typ:

- **Character:** `id sprite flag1 flag2 type level hp mp atk def spd mag items[10] skills[10]`
- **Enemy-Slot:** `instance_id char_id level ai_mode x y team`
- **Partner:** `type level char_id slot`

Wenn du ein neues Feld entschlüsselst, trägst du es in `STAT_FIELDS`,
`DPOS_FIELDS` oder `PARTY_FIELDS` ein. Danach taucht es automatisch im Export
und in Mods auf.

## Mod-Format

```json
{
  "name": "Mein Mod",
  "characters":    {"254": {"hp": 9999, "atk": 99}},
  "characters_vs": {"254": {"hp": 5000}},
  "tower":   {"7": {"map_id": 31}},
  "floors":  {"9": {"enemies":  {"3": {"char_id": 181, "level": 80}},
                    "partners": {"0": {"level": 50}}}}
}
```

- Schlüssel: Char-ID (1-basiert), Floor-Nummer (1-basiert) und Slot-Index (0-basiert).
- Unbekannte Felder, `_raw` und nicht existierende Slots werden abgelehnt. Neue
  Slots anzulegen funktioniert im Spiel nicht zuverlässig (siehe `session-findings.md`).
- **Merge:** `apply` wendet Mods der Reihe nach an. Setzen zwei Mods dasselbe
  Feld auf unterschiedliche Werte, gewinnt der spätere, und es wird eine
  `KONFLIKT`-Zeile ausgegeben.
- Nach dem Anwenden läuft automatisch `validate`. Geprüft werden bekannte
  Crash-IDs, in der Stat-Tabelle inaktive Chars und Chars, die auf demselben
  Floor zugleich Partner und Gegner sind.
