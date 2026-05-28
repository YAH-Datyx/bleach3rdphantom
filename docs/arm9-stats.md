# ARM9 — Charakter-Stat-Tabelle

Reverse-engineering-Notizen zum Stat-Speicherort in `arm9.bin`.

## Fundort

Zwei Stat-Tabellen liegen direkt in `arm9.bin` (kein Overlay):

| Tabelle | Offset | Quelle (Source) | Einträge |
|---|---|---|---|
| Story-Mode | `0xfd882` | `data/yamada/DataBase/db_status.inc` | 255 |
| VS-Mode    | `0xffc56` | `data/yamada/DataBase/db_VSstatus.inc` | ? |

Struct-Größe: **70 Bytes (0x46)** pro Charakter.

## Struct-Layout

| Offset | Größe | Feld          | Hinweis |
|--------|-------|---------------|---------|
| 0x00   | u16   | character_id  | Identisch mit Index (1..255) |
| 0x02   | u16   | sprite_id     | Meist gleich character_id |
| 0x04   | u8    | flag1         | 1 = aktiv, 0 = Platzhalter |
| 0x05   | u8    | flag2         | meist gleich flag1 |
| 0x06   | u8    | type/class    | |
| 0x07   | u8    | level         | |
| 0x08   | u16   | **HP**        | Hitpoints |
| 0x0A   | u16   | **MP** (Reiatsu) | |
| 0x0C   | u8    | **ATK**       | |
| 0x0D   | u8    | **DEF**       | |
| 0x0E   | u8    | **SPD**       | Speed/Initiative |
| 0x0F   | u8    | **MAG**       | Reiatsu-Power |
| 0x10   | 7×u8  | sekundäre Stats | (3, 1, 1, 1, 0, 1, ...) |
| 0x18   | u16   | extra_field_19  | (Wert 40 bei Entry 1) |
| 0x1A   | 10×u16 | item_array     | 20 Bytes |
| 0x2E   | u16   | extra_field_post_items | |
| 0x30   | 10×u16 | skill_array    | 20 Bytes |
| 0x44   | u16   | last_field     | |
| 0x46   | -     | **ENDE**       | nächster Eintrag |

## Verifikation

Diese 5 Einträge konnten gegen `db_status.inc` Zeile für Zeile abgeglichen werden:

| ID | Level | HP    | MP  | ATK | DEF | SPD | MAG |
|----|-------|-------|-----|-----|-----|-----|-----|
| 1  | 17    | 1058  | 119 | 27  | 23  | 27  | 26  |
| 2  | 0 (Platzhalter)                              |
| 3  | 18    | 433   | 46  | 20  | 21  | 32  | 32  |
| 4  | 0 (Platzhalter)                              |
| 5  | 1     | 383   | 25  | 17  | 21  | 24  | 23  |

## Patch-Adressberechnung

```
char_offset = 0xfd882 + (character_id - 1) * 0x46
hp_offset   = char_offset + 0x08
atk_offset  = char_offset + 0x0C
```

Beispiel — Charakter #3, HP von 433 → 9999:
- char_offset = 0xfd882 + 2 * 0x46 = `0xfd90e`
- hp_offset = `0xfd916`
- Bytes ändern: `B1 01` → `0F 27` (9999 als u16 LE)

## Weitere Tabellen in arm9.bin

| Offset | Inhalt | Doc |
|---|---|---|
| `0xfd882` | Story-Mode Stats (255 × 70 Bytes) | hier |
| `0xffc56` | VS-Mode Stats | hier |
| **`0xf3b58`** | **Tower-of-Souls Floor-Tabelle** (30 × 6 Bytes) | siehe `floor-roster.md` |

## Stat-Skalierung in-game

Die Werte in der Tabelle sind **Base-Stats** für Level X (siehe `level`-Feld). Im Spiel werden Stats skaliert:

```
displayed_stat = base_stat + (current_level - base_level) × growth_rate
```

Der `growth_rate` variiert pro Stat und Char-Klasse. Eine globale Mod (z.B. HP=9876 für alle aktiven Chars) wurde verwendet um per-Floor-Char-IDs via Binary Search zu identifizieren — siehe `char-ids.md`.
