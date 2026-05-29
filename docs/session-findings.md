# Session-Findings: Floor- & Char-Mod-Session

Chronologisches Protokoll der größeren Erkenntnisse aus einer Mod-Session, in der Floor 5, 6, 14, 30 modifiziert wurden.

## Reverse-Engineering-Pfad

1. **DeSmuME-Breakpoints geprüft** — Release-Build (0.9.13 x64 SSE2) hat keine funktionierenden Memory-Breakpoints. `dev+`-Build wäre nötig für Live-Debugging.
2. **RAM-Search-Methode** — Char-Stats im Live-RAM gefunden (ab `0x021E7DA0` für Floor-Aktor-Struct), aber Struct-Felder nur teilweise dekodiert.
3. **Statische Analyse** — In `arm9.bin` und `unpacked/data/` nach Stat-Pattern gesucht: Soi Fons exakte Bytes (`18 19 24 24` für ATK/DEF/SPD/MAG = 24/25/36/36) NICHT statisch im ROM → Stats sind level-skaliert.
4. **Tower-Tabelle gefunden** — `arm9.bin @ 0xf3b58`, 30 Floors × 6 Bytes (siehe `floor-roster.md`).
5. **Per-Floor-NARCs identifiziert** — `db_dpos_9XX.narc` (Gegner) + `db_party_9XX.narc` (Partner), 1:1 Mapping zu Floors.
6. **Binary Search für Char-IDs** — Mass-Patch der Stat-Tabelle mit HP-Marker (9876), dann Halbierung bis Soi Fons ID im Range 128-143 lokalisiert.

## Erfolgreich modifizierte Floors

### Floor 14 (Kenpachi-Floor)
- 4 generic „Soul Reaper" Gegner durch named Bleach-Chars ersetzt
- Stats aller Gegner ×1.5 bis ×2 verstärkt (HP, ATK, DEF, SPD, MAG)
- Slot 19 = Fujimaru (Char 200) als Test-Anker behalten

### Floor 5 (Soi Fon Co-Op-Floor)
- Komplett-Content von Floor 30 hinüberkopiert (`db_dpos_930` → `db_dpos_905`)
- Map-ID in Tower-Tabelle: 4 → 31 (Floor 30's Map)
- 24 Slots mit zufälligen Hochlevel-Chars (Lv 78-95) randomisiert

### Floor 6
- Floor-14-Content hinüberkopiert
- 10 zusätzliche Gegner Lv 70-80 hinzugefügt
- Map-ID: 20 → 15 (Floor 14's Map)

### Floor 7 (nicht stabil — crasht)
- Floor-14-Copy + Modifikationen crasht beim Starten
- Map-Reset auf Original (30) testete nicht erfolgreich
- **Hypothese:** Floor 7 hat zusätzliche arm9-spezifische Daten die wir nicht kennen, oder spezifische Floor-Slot-Validierung in arm9-Code

## Wichtige Erkenntnisse / Gotchas

### Char-ID-Konflikte
Wenn ein char_id sowohl als Partner (`db_party_9XX`) als auch als Enemy (`db_dpos_9XX`) im selben Floor vorkommt → Crash. **Squad 11 IDs (21, 23, 25, 27, 29)** sind Partner auf Floor 14/30 → können dort nicht gleichzeitig als Enemy verwendet werden.

### „Filler"-Chars crashen
Manche IDs (100, 145, 146, 147, 150, 175, 195) haben unvollständige Animationen/Stats → Crash beim Spawn. Trial-and-Error nötig um sichere IDs zu finden.

### Map-Mismatch
Tower-Tabelle field2 (map_id) zu ändern funktioniert nicht immer:
- Floor 5 → Map 31 (Floor 30's): ✓ funktioniert
- Floor 6 → Map 15 (Floor 14's): ✓ funktioniert
- Floor 7 → Map 15: ✗ crash (unbekannte Ursache)

### Stat-Skalierung
Base-Tabelle-Werte bei `0xfd882` werden mit Level skaliert. HP=9876 base + level 28 ≈ HP=9976 displayed. Skalierung ist linear pro Stat, mit unterschiedlichen Growth-Rates pro Klasse.

### Char-Klassen
„Type"-Feld im Runtime-Struct (offset +6 im Actor-Struct) entspricht NICHT direkt der char_id, sondern einer Klassifizierung (z.B. type=21 für „Captain-Class"-ähnliche Chars).

## Build-Workflow (etabliert)

```bash
# 1. Mods in unpacked/ machen (arm9.bin oder NARC-Files)
# 2. Repack
./tools/repack.sh

# 3. Patched ROM zum Desktop kopieren (Windows-Pfad)
cp build/Bleach3rdPhantom.patched.nds \
   "/mnt/c/Users/danie/OneDrive - Technische Hochschule Rosenheim/Desktop/Bleach - The 3rd Phantom (Europe) (EnFr)/"

# 4. In DeSmuME: File → Close → File → Open → patched ROM neu laden
#    (NICHT nur Reset — explizit ROM neu öffnen!)
```

## TODOs für nächste Session

- [ ] Floor 7 Crash debuggen — Map-Mismatch oder andere Floor-spezifische Daten
- [ ] dev+ DeSmuME Build installieren für funktionierende Breakpoints
- [ ] Ghidra-Setup für ARM9 (Base: `0x02000000`) — Funktion bei `0x57114` analysieren (referenziert Tower-Tabelle)
- [ ] Weitere Char-IDs verifizieren (besonders 30-99 Range, untested)
- [ ] AI-Modus-Werte durchtesten (field 3 = 10 vs 15 keine sichtbaren Unterschiede bisher)
- [ ] Skill/Bankai-Modifikation — wird Ghidra-Analyse von AI-Decision-Code erfordern

## Session 2 Update (Floor 9 = Floor 12 Copy + Char-ID-Hunting)

### Erkenntnis: Recruit-Aware Logic
Das Spiel detektiert beim Spawn ob ein char_id im Save rekrutiert ist und konvertiert ihn automatisch zum Ally — **egal welches team-Feld** wir setzen. Bestätigt durch User-Save mit 50+ rekrutierten Bleach/3rd-Phantom-Chars.

**Konsequenz:** Echte Tower-Enemies brauchen Char-IDs die nie rekrutierbar sind. Hollow-IDs (154-159, 185, 188, 208, 213, 235) sind die zuverlässigsten.

### Erfolgreiche Floor-Mods (Session 2)

| Floor | Source | Map-ID | Status |
|-------|--------|--------|--------|
| 5 | Floor 30 | 31 | ✓ stabil, 24 Slots mit gemischtem Pool |
| 6 | Floor 14 | 15 | ✓ stabil |
| 8 | Floor 30 | 31 | ✓ stabil, nur Hell Mantis |
| 9 | Floor 12 | 31 | ✓ stabil, 10 Slots mit confirmed pool |
| 7 | — | — | ✗ instabil, mehrere Approaches crashen |

### Neu identifizierte Char-IDs

Aus Floor 9 Testing:
- 144 = Kusaka (recruited → Ally)
- 157 = Frog Head Tech (HP 1528)
- 158 = Frog Head Power (HP 1545)
- 181 = Ukitake (Tech enemy)
- 188 = Matsuri-Variante (namenlos, Power)
- 199 = Kaien (Power)
- 208 = Hisagi (Speed, HP 1501)
- 213 = Evil Eater (Speed Hollow, HP 3501)
- 219 = Urahara Past (Tech)
- 226 = Urahara current (Tech)
- 235 = Matsuri-Variante (namenlos, Speed)

### Neu identifizierte broken IDs
30, 110, 170, 193 — zusätzlich zu früheren {90, 100, 145, 146, 147, 150, 175, 195}

### Erkenntnis: Template-Cloning für neue Slots
Naives Klonen eines belegten Slot-Templates zum Anlegen neuer Enemy-Entries in leeren Slots **funktioniert nicht zuverlässig** — Floor 9 mit 20 neu-angelegten Slots zeigte 0 Enemies trotz Template-Übernahme. Sicherer ist: **nur existierende Slots überschreiben** (char_id + level ändern), nichts Neues anlegen.

### Floor-Mode-Mismatch
Floor 7 crasht mit Map-15 UND Map-30 UND Map-31, selbst mit pure Original-Daten. Floor 9 funktioniert mit Map-31. Unklar warum Floor 7 spezifisch problematisch ist — vermutlich Floor-spezifischer Code in arm9 oder Overlay.
