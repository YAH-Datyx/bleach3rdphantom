# DB-Tabellen in arm9.bin (an der ROM YBTP verifiziert)

Gefunden mit `python3 tools/re/find_db_tables.py`. Jede Tabelle hat eine
Getter-Funktion nach demselben Muster: Sie läuft bis zum Terminator `-1` durch
die Tabelle und gibt einen Zeiger auf den Eintrag mit passendem Schlüssel
zurück, sonst 0. Die Zuordnung zu den `.inc`-Dateien in
`data/yamada/DataBase/` beruht auf den Eintragszahlen. Diese Dateien sind die
Quell-CSVs der Entwickler als C-Initialisierer, z. B. `{ 1,33,1, }`. Sie haben
keine Spaltennamen, liefern aber Feldreihenfolge, Gruppen und Array-Längen.

| Getter (RAM) | Tabelle (RAM) | arm9-Offset | Eintrag | Einträge | Quelle (.inc) | Inhalt |
|---|---|---|---|---|---|---|
| `0x02056F98` | `0x020F3AE4` | `0xf3ae4` | 4 B | 28 | db_matching? | ? |
| `0x020570E4` | `0x020F3B58` | `0xf3b58` | 6 B | 30 | db_btower | Tower-Floors (siehe floor-roster.md) |
| `0x020570AC` | `0x020F3DEC` | `0xf3dec` | 10 B | 29 | db_fbattle | Floor-/Free-Battles (enthält 801…, wie db_dpos_8XX) |
| `0x02056F64` | `0x020F4488` | `0xf4488` | 6 B | 215 | db_f_partner | |
| `0x02057078` | `0x020F4998` | `0xf4998` | 0x44 | 45 | db_result | Ergebnis/Belohnungen? |
| `0x02057040` | `0x020F55D0` | `0xf55d0` | 0x20 | 173 | db_ability_selection | |
| `0x02056EC8` | `0x020F6B90` | `0xf6b90` | 0x32 | 117 | db_skill | Skills (+ Namen in db_skill_name.bin) |
| `0x02056F30` | `0x020FAC3C` | `0xfac3c` | 0x2C | 255 | db_partner | pro Char: Partner-/Lernlisten |
| `0x02056E58` | `0x020FD83C`* | `0xfd882` | 0x46 | 255 | db_status | **Story-Stats** (arm9-stats.md) |
| `0x02056E94` | `0x02101E84` | `0x101e84` | 0x4C | 265 | db_growt | **Level-Wachstum** |
| `0x02056EFC` | `0x02106D7C` | `0x106d7c` | 0x92 | 521 | db_ability | Fähigkeiten |
| — | `0x0211A938` | `0x11a938` | 0x46 | 37 | db_VSstatus | **VS-Stats** (gleiches Layout wie Story) |

\* Der Getter lädt Basis − 0x46 und vergleicht `id` bei +2.

Weitere Hilfsfunktion: `0x02056E0C` `CharIdToModel(id)` gibt das `model`-Feld
(+0) des Stat-Eintrags zurück. IDs ≥ 500 reicht sie unverändert durch.

## Aufrufer (Spur zur Spiellogik)

Alle Overlays werden an `0x0215B5A0` geladen, es ist immer nur eines aktiv.

| Funktion | Aufrufer |
|---|---|
| `GetTowerFloor` | nur **Overlay 1**: `0x02189A84`, `0x02189F00` → Floor-Setup/Spawn, Kandidat für Enemy-Cap und Floor-7-Crash |
| `GetFBattle` | Overlay 6: `0x0215CED0` |
| `GetCharStatus` | arm9 (9×), Overlay 1 (5×), **Overlay 6 (15×, vermutlich Kampf)**, Overlay 8 |
| `CharIdToModel` | arm9 (9×), Overlay 1 (6×), Overlay 6 (8×), Overlay 8, Overlay 10 |

## Nächste Schritte

1. Overlay 1 in Ghidra laden (Basis `0x0215B5A0`) und die beiden
   `GetTowerFloor`-Aufrufer decompilieren. Dort sollten Map-Laden,
   `db_dpos`/`db_party`-Laden und die Spawn-Schleife mit ihrem Limit stehen.
2. Layouts von db_growt, db_skill und db_ability aus den `.inc`-Feldfolgen
   ableiten und in `gamedata.py` aufnehmen.
3. In Overlay 6 bei den GetCharStatus-Aufrufern nach der Schadensformel suchen.
