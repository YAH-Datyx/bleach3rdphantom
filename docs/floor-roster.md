# Floor-Roster & Tower-System

Reverse-engineering-Notizen zum Tower-of-Souls-System und den per-Floor-Datenstrukturen.

## Tower-Tabelle

**Ort:** `arm9.bin` Offset `0xf3b58` (RAM-Adresse `0x020F3B58`)
**Layout:** 30 Einträge × 6 Bytes (3 × u16), terminiert mit `FF FF 00 00`
**Größe:** 180 Bytes

Pro Eintrag:

| Offset | Größe | Feld | Beschreibung |
|--------|-------|------|--------------|
| 0x00 | u16 | floor_num | 1..30 (Floor-Nummer) |
| 0x02 | u16 | map_id | Map-/Encounter-ID |
| 0x04 | u16 | floor_echo | meist == floor_num |

**Quelldokumentation:** `data/yamada/DataBase/db_btower.inc` (CSV-Text, kann veraltet sein — die kompilierte Tabelle in arm9 ist die Wahrheit)

Beispiele (aus arm9):

```
Floor  1: { 1, 34,  1}
Floor  5: { 5,  4,  5}
Floor 14: {14, 15, 14}
Floor 30: {30, 31, 30}
```

## Per-Floor-Dateien (1:1 Mapping)

Jeder Floor hat genau zwei NARC-Dateien im `unpacked/data/yamada/DataBase/`:

| Datei | Inhalt |
|---|---|
| `db_dpos_9XX.narc` | **Gegner/Deployment** (Position + Char-ID + Level pro Spawn) |
| `db_party_9XX.narc` | **Partner/Allies** (Co-Op-Roster pro Floor) |

`XX` = Floor-Nummer (z.B. `db_dpos_914` für Floor 14).

## `db_party_9XX.narc` Format

Sub-File 0, klein (~100 Bytes).

- **Header**: `01 00 00 00` (4 Bytes — vermutlich Magic/Count)
- **Pro Partner-Entry** (14 Bytes = 6× u16 + 2-Byte-Terminator):

| Offset | Feld | Hinweis |
|---|---|---|
| 0x00 | type | immer `0x000a` (=10) |
| 0x02 | level | z.B. 30 für Lv 30 |
| 0x04 | char_id | Verweis auf Char-Stat-Tabelle |
| 0x06 | ? | meist 2 oder 3 |
| 0x08 | ? | meist 1 |
| 0x0A | slot | 2..N, Position im Roster |
| 0x0C | terminator | `00 00` |

**Floor 14 Beispiel:**

```
Lv 30, char 21 (Kenpachi), slot 2
Lv 30, char 23, slot 3
Lv 30, char 25, slot 4
...
```

## `db_dpos_9XX.narc` Format

Sub-File 0, groß (~6.9 KB). Bis zu 128+ Slots, viele leer.

**Pro Slot:** 54 Bytes (`0x36`).

| Offset | Feld | Beschreibung |
|---|---|---|
| 0x00 | u16 instance_id | Sequentielle ID (z.B. 784+) |
| 0x02 | **u16 char_id** | Char-Template aus Stat-Tabelle |
| 0x04 | **u16 level** | Spawn-Level |
| 0x06 | u16 ai_mode | 15 = passiv/patrol, 10 = aktiv/boss |
| 0x08 | u16 grid_x | Tile-Position X |
| 0x0A | u16 grid_y | Tile-Position Y |
| 0x0C | u16 | meist 2 |
| 0x0E | u16 team | 1 = Standard-Gegner, 10/11 = Boss-Team |
| ... | ... | restliche Felder oft 0; gelegentlich items/skills bei +0x12 |

Leerer Slot = alle Bytes nach `[0:4]` sind 0.

## Floor-Daten ändern: Workflow

1. **Char-Liste anschauen:**
   ```python
   import ndspy.narc, struct
   narc = ndspy.narc.NARC.fromFile('unpacked/data/yamada/DataBase/db_dpos_914.narc')
   ENTRY = 54
   f0 = narc.files[0]
   for i in range(len(f0)//ENTRY):
       cid = struct.unpack_from('<H', f0, i*ENTRY+2)[0]
       lvl = struct.unpack_from('<H', f0, i*ENTRY+4)[0]
       if cid != 0:
           print(f'Slot {i}: char={cid}, lvl={lvl}')
   ```

2. **Char ersetzen** (z.B. Slot 19, neuer char_id 200, Level 80):
   ```python
   f0 = bytearray(narc.files[0])
   off = 19 * 54
   struct.pack_into('<H', f0, off+2, 200)
   struct.pack_into('<H', f0, off+4, 80)
   narc.files[0] = bytes(f0)
   narc.saveToFile('unpacked/data/yamada/DataBase/db_dpos_914.narc')
   ```

3. **Repacken & laden:**
   ```bash
   ./tools/repack.sh
   ```

## Floor auf anderen Floor "spiegeln"

Floor X soll Floor Y's Inhalt haben:

```bash
# Daten kopieren
cp unpacked/data/yamada/DataBase/db_dpos_9YY.narc unpacked/data/yamada/DataBase/db_dpos_9XX.narc
cp unpacked/data/yamada/DataBase/db_party_9YY.narc unpacked/data/yamada/DataBase/db_party_9XX.narc

# Map-ID in Tower-Tabelle anpassen
python3 -c "
import struct
d = bytearray(open('unpacked/arm9.bin','rb').read())
off = 0xf3b58 + (X-1)*6  # Floor X
struct.pack_into('<H', d, off+2, FLOOR_Y_MAP_ID)
open('unpacked/arm9.bin','wb').write(bytes(d))
"
```

## Bekannte Crashes / Gotchas

- **Char_id Conflict Partner↔Enemy**: Wenn derselbe char_id sowohl in `db_party_9XX` (Partner) als auch in `db_dpos_9XX` (Enemy) vorkommt, kann das Spiel crashen
- **„Filler-Chars" crashen**: Einige Char-IDs (z.B. 175, 195, 100, 145-150) haben kaputte Animations/Stats und crashen das Spiel. Verifiziere jeden neuen Char einzeln
- **Stat-Skalierung**: Displayed Stats kommen aus `arm9.bin[0xfd882] + Level-Growth`. Patches an der Base-Tabelle wirken auf ALLE Vorkommen des Chars im Spiel
- **Map-Mismatch**: Floor-X auf Floor-Y's Map zu setzen klappt manchmal, manchmal nicht (Floor 7 mit Map 15 crashed, Floor 6 mit Map 15 läuft)
