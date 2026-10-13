# Bleach: The 3rd Phantom (NDS, Europe) — Reverse-Engineering-Report

Übergabe-Dokument: Stand aller Erkenntnisse, damit die Arbeit in einem
neuen Chat / auf einem anderen Gerät nahtlos weitergehen kann.

## 0. Setup

- **ROM-Basis:** `Bleach - The 3rd Phantom (Europe) (En,Fr).nds` (128 MB,
  Gamecode `YBTP`, Header-Titel `BLEACH 3RD`). Aktuelle Arbeits-ROM =
  `Bleach3P modded.nds` in diesem Ordner (DEFAULT_ROM in `tools/romfs.py`);
  `Bleach3P_test_mod.nds` = Quasi-Vanilla-Referenz. Details: Abschnitt 8/10.
- **Toolkit:** reines Python 3 (keine Abhängigkeiten), GUI = tkinter.
  Editor starten: `python stat_editor.py` (oder `Editor starten.bat`).
  Selbsttest: `python stat_editor.py --selftest`.
- ARM9 ist **unkomprimiert** (0x4000 im ROM, 0x142AF8 groß, RAM 0x2000000).
  6126 benannte Dateien im NitroFS + 25 unbenannte FAT-Einträge (Overlays,
  FAT-IDs 6126–6150; Overlay-Reihenfolge = FAT-Reihenfolge).

## 1. Dateisystem-Landkarte (wichtigste Pfade)

| Pfad | Inhalt |
|---|---|
| `/yamada/DataBase/db_btower.inc` | Bleach Tower: 30× `{Etage, MapID, PartyIdx}` — **liegt AUCH binär im ARM9 @0xf3b58** (u16-Tripel), .inc evtl. nur Build-Rest! |
| `/yamada/DataBase/db_dpos_NNN.narc` | Einheiten pro Kampf. Turm = 901–930, Story = 000–264, Free Battle = 8xx, VS = 5xx/7xx |
| `/yamada/DataBase/db_party_NNN.narc` | Spieler-Deploy-Slots pro Kampf (Turm: 8 Slots à 14 B) |
| `/yamada/DataBase/db_status.inc` | Charakter-Basiswerte, 255 Zeilen Klartext |
| `/yamada/DataBase/db_growt.inc` | Level-Up-Wachstum: pro Char 7×4-Matrix (7 Stats: HP, SP, ATK, DEF, HIT, EVA, **S-Pressure**) |
| `/yamada/DataBase/db_skill.inc` | 116 Battle-Skills (Kidō etc.), Klartext |
| `/yamada/DataBase/db_ability.inc` | 521 Ability-Definitionen |
| `/yamada/DataBase/db_fbattle.inc` | Free-Battle-Liste `{Nr, StoryRef, PartyId, MapID, GegnerLevel}` |
| `/yamada/ScrDat/s_name.bin` | **Namenstabelle**, 371 Einträge, Index = Charakter-/Unit-ID |
| `/yamada/DataBase/db_skill_name.bin` / `db_skill_help.bin` | Skill-Namen (112) / Hilfetexte |
| `/yamada/DataBase/db_ability_name.bin` / `db_ability_msg1.bin` | Ability-Namen (298 benannt von 513) / Texte |
| `/yamada/NCface/nc_FFFVV.bin` | Porträts (FFF = Face-ID = Spalte 4 in db_status, VV = Mimik 01+) |
| `/kuro/nc_main/bat_main_ncPPP.bin` | Battle-Sprites (PPP = Person-ID = Spalte 0 in db_status); nur 104 IDs vorhanden! |
| `/yamada/FMap/MAPxxy.bin` | Spielfeld-Karten (34 Stück + Kumo.bin) |
| `/yamada/minimap/map.cpk` | Minimaps (CPK-Archiv, noch nicht dekodiert) |
| `/kuro/etan_bak/MM_VVbs.bin` | Kampf-Hintergründe (gleiches MM_VV-Schema wie Maps) |

**Sprachvarianten:** fast alles doppelt mit `_fre`-Suffix (Französisch).

## 2. Dateiformate

### 2.1 `.inc` = Klartext-Tabellen (C-Initializer)
Zeilenweise `{ a, b, {c, d}, ... },` mit CRLF. Direkt editierbar.
**Patch-Regel:** Datei darf nicht größer werden; der Editor ersetzt nur
Zahlen-Tokens und füllt am Ende mit Spaces auf Originalgröße auf.
**Offene Frage:** db_btower existiert doppelt (.inc + ARM9-Binärtabelle) —
ungeklärt, welche Quelle die Engine liest. db_party wird sicher aus dem
Dateisystem geladen (Formatstring `db_party_%03d.narc` im ARM9 @0x138318),
db_dpos + FMap sicher aus Overlay 1 (`db_dpos_%03d.narc` @0x3c000,
`/yamada/FMap/MAP%03d.bin` @0x3a030).

### 2.2 BGSM = Textdateien (UTF-16LE)
Header: `BGSM`, u32@0x0C = Basis (0x10), u32@0x10 = Anzahl, dann
u32-Offsets (relativ zur Basis, 0xFFFFFFFF = leer), Strings nullterminiert.
Decoder: `formats.bgsm_strings()`.

### 2.3 NARC
Standard-Nitro-Archiv (BTAF/BTNF/GMIF). `formats.narc_subfiles()` /
`narc_replace_subfile()` (nur gleiche Subfile-Größe).

### 2.4 Huffman-Container (Porträts, Karten, Status-Grafiken)
NCface- und FMap-Dateien sind **BIOS-Huffman Typ 0x28** komprimiert
(u32-Header: Typ|Größe<<8, Baumgröße-Byte, Baum, 32-bit-Bitstream).
Decoder: `faces.huff_decompress()`. **Ein Packer existiert noch nicht** —
Grafik-Mods erfordern, ihn zu schreiben (BIOS-kompatibel, machbar).

### 2.5 Porträts (NCface)
Huffman → NARC → [NCGR, NCLR]. NCGR-Pixel sind **linear** (kein Tiling!),
128×64 8bpp; linke 64×64 = Gesicht. Farbe 0 = transparent.
`faces.face_png(fs, face_id, variant)` → PNG-Bytes.

### 2.6 Spielfeld-Karten (FMap)
Huffman → NARC mit 7 Subfiles: RGCN-Tileset (1024 Tiles 8bpp), RLCN
(16×256 Farben), RCSN-Tilemap, RNAN/RGCN/RECN (Animationen), RLCN.
Tilemap-Größe variiert (z. B. 512×384). **Karten > 256 px sind in
256×256-px-Screenblöcken gespeichert** (32×32 Tiles, Randblöcke schmaler,
Blöcke zeilenweise). Entry: u16, Bits 0–9 Tile, 10/11 Flip, 12–15 Palette
(praktisch immer 0). Renderer: `fmap.decode_map()` / `map_png()`.
**1 Spielfeld-Zelle = 8×8 px** (empirisch verifiziert).

### 2.7 Map-ID → Datei
`db_btower` Spalte 2 / `db_fbattle` Spalte 4 = Map-ID 0–39.
Übersetzung über 40er-u16-Tabelle in **Overlay 1 @ 0x3ada8** (0-basiert):
`[11,21,31,32,41,51,61,71,81,82,91,92,101,111,121,131,141,151,161,162,171,181,191,192,193,201,221,222,231,232,241,251,252,271,291,321,331,351,361,381]`
→ `MAP{wert:03d}.bin`. Einträge 7,19,22,26,36,38 haben keine Datei (ungenutzt).
Beispiel: Etage 1 → MapID 34 → MAP291. Kopie der Tabelle: `fmap.MAP_TABLE`.

## 3. Datenstrukturen

### 3.0 VANILLA-AUFBAU-MUSTER (Analyse 2026-07-08, aus test_mod.nds)
Wie das Original Kaempfe strukturiert — Referenz fuers Level-Bauen:

**Turm-Etagen (901–930):**
- **Deploy-Slots:** IMMER 8, IMMER als kompakter **2-Spalten-Block**
  (3×7, 7×3, 3×9 …), NIE verstreut. Liegen am RAND der begehbaren
  Flaeche (Spieler-Startecke), nicht in der Mitte.
- **Gegner-Zentrum liegt fast immer bei ~(18–22, 19–21)** = grob
  Kartenmitte; die Deploy-Zone sitzt versetzt dazu (eine Ecke/Seite).
  Team-Abstand (Deploy-Zentrum↔Gegner-Zentrum) meist **8–14 Felder**.
- **Gegner streuen breit** (bbox oft halbe Karte), stehen NICHT in einer
  Linie — lockere Wolke um die Mitte, teils gestaffelt (vorne schwache,
  hinten starke). Anzahl initial platziert: Etage 1–30 =
  14,14,9,13,18,14,13,9,18,11,10,10,13,8,12,10,13,11,14,14,11,13,17,25,
  10,11,12,6,10,13.
- **Wellen/Verstaerkung:** Records mit x=y=0 (keine Startposition)
  tauchen erst ab Etage 20 auf und werden gegen Ende dominant
  (F28: nur 2 initial, 36 als Welle!). Die Engine laedt sie ueber
  dpos-Subfile 1 nach (Spawn-Gates, Bedeutung teils offen).

**Story-/Chapter-Kaempfe (000–264):**
- **Team-Byte-Nutzung gesamt:** 3 (Gegner) 620x, 1 (Spieler-vorplatziert)
  163x, 2 (neutral/Verbuendeter?) 28x, 5 (Spezialobjekt) 24x, 4 (selten) 6x.
- **~50/50-Split:** die Haelfte der Story-Kaempfe hat FEST vorplatzierte
  Team-1-Verbuendete (Story-Party an fixen Feldern, KEIN freies Deploy),
  die andere Haelfte nur Gegner (freies Deploy wie im Turm).
- **Gegner deutlich WENIGER gestreut als im Turm** (spread ~4–8 vs Turm)
  — engere, oft an einer Kartenseite geclusterte Formationen (Story-Inszenierung).
- **Team 2** = neutrale/eskortierte NPCs (Drunk Reaper, Rukon-Zivilisten,
  Yoruichi, Konoka) — stehen mit den Gegnern, greifen aber anders an.
- **Team 5** = Spezial-OBJEKTE, immer "Sky Rift" (spawnt periodisch
  Hollows, s. Tutorial [15]) — NIE als normaler Kaempfer.

**Fazit fuers Bauen:** Deploy immer als 8er-Randblock; Gegner als lockere
Wolke um die Kartenmitte mit 8–14 Feldern Abstand zur Deploy-Ecke; starke
Gegner hinten. Fuer Story-Feeling: Verbuendete/Objekte per Team 1/2/5
fest setzen. (Der Editor-Randomizer bildet genau dieses Muster nach.)

### 3.1 db_status.inc (42 Zahlen-Tokens pro Zeile)

> **KRITISCH (in-game verifiziert 2026-07-03): db_status.inc ist nur ein
> BUILD-ARTEFAKT — die Engine liest die kompilierte Stat-Tabelle im ARM9
> bei ROM-Offset `0x101C52 + (unit−15)·70`** (auch für unit<15 gültig,
> Records liegen davor; Prüf-Key: u16 @+6 == unit). Record-Layout (70 B):
> +4 u16 person, +6 u16 unit, +8 typ, +9 unk3, +10 face, +11 lv,
> +12 u16 hp, +14 u16 sp, +16 atk, +17 def, +18 hit, +19 eva, +20 mov,
> +21 aType, +25 unk17, +26 S-Pressure, +28 u16[10] Equip, +48 u16 unk20,
> +50 u16[10] Fähigkeiten. atk/def/hit/eva sind u8 → Werte ≤ 255 halten!
> Der Editor spiegelt beim Speichern alle .inc-Werte automatisch dorthin
> (`_sync_arm9_status`). Verdacht: db_skill.inc/db_growt.inc sind ebenfalls
> Artefakte (ARM9-Growth-Tabelle vermutlich @0x105E84 + unit·76, aus dem
> Vorgänger-Projekt bekannt) — vor Verlass darauf in-game testen!
`{person, unit, typ, unk3, face, lv, hp, sp, atk, def, hit, eva, mov, attribut, unk14..unk17, spressure?, {equip×10}, unk20, {abilities×10}, unk22, unk23}`
- **person** (Spalte 0) → Battle-Sprite `bat_main_nc{person:03d}.bin`
- **unit** (Spalte 1) → eindeutige ID, = Index in s_name.bin
- **typ** (Spalte 2): 1 = spielbar/verbündet (119 Stück), 3/4/5/6 = Gegnerklassen, 0 = leer
- **face** (Spalte 4) → NCface-Nummer
- Statreihenfolge lt. Tutorial-Text: HP, SP, Attack, Defense, Accuracy,
  Evasion, Spiritual Pressure (= Zusatzschlag-Chance, im Kampf aufladbar)
- Spalte 13 = Kampf-Attribut (13 = Spezial „All", z. B. Prolog-Gin, Arturo)
- Spalte 18 = vermutl. S-Pressure-Startwert (Yamamoto 40, Kenpachi 37, Rukia 0)
- abilities-Liste: erstes Element = Zähler/Typ?, dann Ability-IDs
- unk14–17, unk20, unk22, unk23: **ungeklärt**

### 3.2 Sichere vs. unfertige Einheiten (Crash-Schutz!)
Einsetzbar nur wenn: `typ != 0` **und** `hp > 0` **und** Battle-Sprite
`bat_main_nc{person}.bin` existiert → **195 sichere Einheiten**.
60 unfertige (49 ohne Stats: Sasakibe, Omaeda, Isane …; 11 ohne Sprite:
Zivilisten/Tentacle/Zanpakuto) + 71 reine Dialog-Sprecher (IDs 301+)
→ crashen das Spiel. Der Client blendet sie aus und blockt hart.

### 3.3 db_dpos_NNN.narc (Einheiten eines Kampfes)
Turm-Version: 4 Subfiles. **Subfile 0** = 128 Records à **54 Bytes**:
`u8 slot(1-basiert), u8 TEAM, u16 char, u16 level, u16 unk3, u16 x, u16 y, u16 dir(0-3), u16 unk(=1), u16 raw[18] (AI/Extras)`

> **unk3 (u16 direkt hinter dem Level): Bedeutung UNBEKANNT.**
> ⚠️ **KORREKTUR 2026-10-13:** Die frühere Behauptung (2026-07-25),
> Tower-Gegner bräuchten `unk3=15` und `unk3=10` lasse die HP-Berechnung
> kollabieren (53/11 HP), ist **WIDERLEGT**. Eine vollständige Auszählung
> aller 30 Vanilla-Etagen zeigt gemischte Werte:
> `0, 10, 13, 15, 17, 18` — die **Mehrheit der Etagen nutzt 10**
> (z. B. Etage 1/2/3/8/16: ausschliesslich 10; Etage 11: 13;
> Etage 14/15: 15; Etage 28: 0). unk3 ist also **kein Stat-/HP-Flag**.
> Auch der Randomizer schreibt seit jeher `unk3=10` (`pack_units`-Default)
> und erzeugt funktionierende Gegner.
> **Der HP-Bug (53/11) ist WEITERHIN OFFEN** — aktueller Hauptverdacht:
> die Zufalls-Skills überschreiben die Fähigkeiten **370 und 401**, die
> jeder Vanilla-Kampfchar trägt. Details + nächster Testschritt in
> **HANDOVER.md Abschnitt 5**.
Turm: Slots 1–15 Spieler-/Reserve (leer), ab 16 Gegner.
**Byte 1 ("aktiv") ist das TEAM: 3 = Gegnerseite (alle normalen Turm-Gegner),
1 = Spielerseite, 5 = Spezial-Objekt (Sky Rift auf Etage 28)** — in-game
verifiziert: Einheiten mit 1 spawnen im Player-Team.
**ACHTUNG: typ=1-Charaktere (Spieler-Roster, db_status Spalte 2) ziehen als
Gegner ihre Level/Stats aus dem SPIELSTAND, nicht aus dem dpos-Level!**
In-game verifiziert: Rangiku (47) mit dpos-Lv 78 spawnte als Lv 20/Exp 46
(= ihr Save-Stand). Für starke Gegner die Enemy-Varianten nehmen
(IDs 132–144 Captains, 196–254 Story-Chars: Ichigo 241/254, Rangiku 209,
Kenpachi 141, Uryu 243 …).
**Kaputte Einheiten (RANDOMIZER_BLACKLIST im Editor): 176/177 "Whole"
(Demi-Hollow-Geister, in-game kaputt — User-verifiziert), 185 "Sky Rift".**
**db_partner.inc Token 1 = ROSTER-FLAG:** 1 = Charakter kann ins Spieler-
Roster (Rangiku 47, Ulquiorra 114, Yammy 118, Arturo 130, Shinji 179,
Hiyori 180, Chad 95, Uryu 96, Orihime 97, Kon 101, Don Kan'onji 112 …) →
zieht als Gegner Level/Stats aus dem SPIELSTAND (in-game verifiziert an
Rangiku und Shinji). Reine Enemy-Kopien haben Flag 0 (209, 242, 247, 113,
115, 117, 129 …). **WICHTIG: typ=1 allein heisst NICHT Save-verknuepft —
nur Partner-Flag=1 zaehlt!** (Batch-verifiziert: alle typ=1+Flag=0-Einheiten
inkl. Captains skalieren exakt mit dem dpos-Level.)
**Randomizer-Pool = VERIFIED_POOL_IDS in stat_editor.py: 111 IDs, JEDE
einzeln in-game verifiziert (Batch-Tests 1-10 auf Etage 1, exaktes Level
45/90 geprueft). Nur noch die namenlosen IDs 200-205/210-215/220-225/
230-235 sind ungetestet.**
**dpos raw-AI-Felder: raw[1] = AI-Typ, raw[2] = Aggressivität (0–100).**
Vanilla-Muster: 3/100 = jagt den Spieler aktiv, 0/0 = wartet defensiv bis
zur Annäherung. Im Editor pro Einheit editierbar (Felder „ai"/„aggro")
und im Randomizer als Verhalten Original/Aggressiv/Defensiv wählbar.
**AI-DEEP-DIVE (2026-07-08, alle 204 Kaempfe der Vanilla-Ref analysiert):
raw[1] ist eine SKRIPT-ID, und die VS-/Challenge-Kaempfe (7xx, dort
zuenden Captains in-game Bankai!) vergeben CHAR-SPEZIFISCHE Typen:**
Byakuya=11, Kenpachi/Arturo/Ichigo/Grimmjow(frueh)=12, Hitsugaya=2,
Komamura=16, Grimmjow(spaet)=15, Mayuri=7, Tosen=18, Renji-Gruppe=19/4,
Unohana-Person=8 (Kampf 723 = alle Captains mit diesen Typen + Aggro
100). Vermutung: Bankai-Zuendung steckt in diesen Skripten (alter
Fehlversuch nutzte nur Typ 3 = simpler Jaeger).
TEST LAEUFT: Etage 3 = 8 Captains Lv50, jeder mit seinem VS-AI-Typ.
Weitere raw-Beobachtungen: raw[0] = kleine Zahlen 2-7 ODER 65533/65535
(-3/-1; Wellen/Gruppen?), raw[3] = Low-Byte 1-8 + High-Byte-Flags
(0x200/0x300/0x400/0x500), raw[10] = reine 0x100-Stufen (256-2560,
Verdacht: Drop-/Belohnungs-Slot), raw[4..8] = teils Koordinaten-artige
Paare (Patrouillen-Punkte?).
**SPRITE-/EINHEITEN-LIMIT — FINAL BISEKTIERT (Etage 1, 2026-07-06):
25 Gegner mit 25 VERSCHIEDENEN Sprites = OK, 26 = CRASH (3x bestaetigt:
2x festes Captain-Set inkl. deterministischem Retest mit identischem
Seed, 1x Zufalls-Set ohne Riesen)** — es ist die ANZAHL, nicht das Set.
Datenreihe (identisches Skript, nur N variiert, ohne Riesen, 8
Deploy-Slots): 16/18/20/22/24/25 OK, 26/28 CRASH. Ebenfalls bewiesen: **EXTRA-SLOTS
ueber die initialen Vanilla-Slots hinaus funktionieren** (Etage 1 hat
14 Vanilla-Slots, Tests liefen sauber bis Slot 40) — die alte Regel
"nur Original-Slots nutzbar" ist hinfaellig; der alte 27-Gegner-Crash
auf Etage 14 (07-03, "23 unique = Crash") war wohl schlicht das
25er-Limit bzw. Riesen im Set.
Editor-Umsetzung: MAX_UNIQUE_SPRITES = 25 (Randomizer + Selftest),
Randomizer fuellt fehlende Slots als Extra-Slots hinter dem letzten
Vanilla-Slot auf und laesst Riesen-Sprites weg: BIG_UNITS = Grand
Savage 148-150, Menos Grande 163-165, Huge Hollow 166-168, Jidanbo
237, Giant Entity 252 (manuell bleiben sie setzbar).
**Blickrichtung (dpos dir 0-3): 0=Ost/+x, 1=Nord/-y, 2=West/-x,
3=Sued/+y** — aus Vanilla-Statistik aller 30 Etagen abgeleitet und
in-game bestaetigt (22er-Test: Gegner schauten zur Deploy-Zone,
"fuer die meisten" korrekt — Rest evtl. Diagonalfaelle).
**Etagen-Kapazitaet (AKTUALISIERT 2026-07-06): Extra-Slots ueber die
initialen Vanilla-Slots hinaus sind nutzbar** — der alte Etage-14-Crash
(27 Gegner) war das 25er-Sprite-Limit, nicht die Slot-Anzahl. Viele
Einheiten grosser Etagen sind Wellen-Verstaerkungen OHNE Startposition
(x=y=0; Etage 28: nur 6 von 42 initial!). Der Randomizer nutzt die
Vanilla-Slot-Templates aus `dumps/vanilla_ref.json` (slot/active/raw)
zuerst und haengt bei Bedarf Extra-Slots (active=3, raw von Template 0)
bis MAX_UNIQUE_SPRITES=25 an. (Initiale Vanilla-Slots pro Etage 1–30:
14,14,9,13,18,14,13,9,18,11,10,10,13,8,12,10,13,11,14,14,11,13,17,25,
10,11,12,6,10,13.)
`vanilla_ref.json` enthaelt auch die Vanilla-Basisstats aller Einheiten —
Boosts rechnen immer von dort (idempotent, kein Aufschaukeln mehr).
**Subfile 1 = AI-SKILL-/FAEHIGKEITEN-SCRIPTS PRO EINHEIT (GEKNACKT
2026-07-08):** 36-u16-Header (Reihenfolge-/Index-Liste 1..N) + ein
36-u16-BLOCK JE EINHEITEN-RECORD, in SLOT-Reihenfolge (Block N = N-ter
Record, idx = N+1 im Block-Header-Low-Byte). Ein Block =
`u16 header((?<<8)|idx), dann u16[] = SKILL-IDs (db_skill), gefolgt von
passiven ABILITY-IDs (db_ability), Rest mit 0xFFFF/0 gepolstert`. **Das
ist der Skill-Pool, aus dem die GEGNER-AI im Kampf waehlt** - separat von
der ARM9-Ability-Liste (= Charakter-Definition). VERIFIZIERT: der
Heiler-NPC Konoka hat im Block nur Heil-Skills (Keikatsu/Meiyu/Shikuka/
Kokkai) -> heilt in-game; Kido-Gegner haben Sokatsui/Byakurai etc.;
Wellen-Verstaerkungen (x=y=0) haben leere/minimale Bloecke -> nur
Nahkampf. **PRAKTISCH: hier laesst sich die Gegner-Skill-Nutzung
editieren (smartere/thematische Gegner) - Groesse pro Block bleibt (36
u16).** Der Block-Header-High-Byte (frueher als "X" fehlgedeutet) ist
KEIN Spawn-Gate und keine Position.
**Wellen-SPAWN-TRIGGER selbst (welche Einheit wann nachkommt) liegt NICHT
in den Subfiles, sondern im Kampf-/Story-Code** - Wellen-Records tragen
nur ihr AI-Block; die Engine platziert sie bei Ausloesung (Code-seitig,
wie Bankai nur per RE weiter aufloesbar).
**x/y sind 1-BASIERT** (Grid-Zelle = x−1, y−1)! Verifiziert: alle 739
Einheiten+Deploy-Slots aller 30 Etagen stehen so exakt auf Wert-10-Feldern
von Subfile 2. aktiv=3 = Spezial-Record (Verstärkung?, oft x=y=0).
**Subfile 2 = 39×39-Terrain-Grid: 10=begehbar, 0=Rand/Deko (NICHT
begehbar), 255=außerhalb.** Subfile 3 = 39×39-Grid, Bedeutung unklar
(NICHT die Deploy-Zone — Party-Slots liegen bei keinem konstanten Offset
darauf). Story-dpos (z. B. 000): 1 Subfile, gleiche Records.
Achtung: leere Records haben je nach Slot aktiv=0 ODER 1 — beim Packen
Originalbytes erhalten (`tower.pack_units` macht das korrekt).

### 3.4 db_party_9NN.narc (Turm-Deploy-Slots)
Subfile 0: 8 Records à 14 B: `u32 id, u16 unk(=10), u16 x, u16 y, u16 unk, u16 unk`.
= Startpositionen der vom Spieler gewählten Charaktere.

### 3.5 db_skill.inc (116 Zeilen, 17 oder 20 Tokens)
`{id, ?, ?, {{typ,"power",wert}×1–2}, ?, ?, "sp_kosten", ...11 weitere}`
Effektanzahl = (Tokenzahl−14)/3; Kosten-Token = 3+3n+2.
**EFFEKT-TYP-TAXONOMIE (2026-07-08, aus Hilfetext-Korrelation):**
0 = keiner, 1 = Schaden, 2 = Gift/Heilung (wert<999 = Gift-Chance,
999 = Heilung auf Verbuendete), 3 = Burn/Multi-Move, 4 = Freeze bzw.
SP-Heilung, 5 = Shock, 6 = DEF+, 7 = ACC+, 8 = EVA+, 13 = Status-Cure,
15 = HP-Drain, 16 = Zufalls-Ailment, 18 = S-Pressure+, 19 = Pressure-
Drain, 20 = Eis-Einschluss (Sennenhyoro), 22 = Pressure-Senkung
(Seeleschneider), 24 = Homonka (Nigeki Kessatsu). power = Staerke,
wert = Chance % (999 = sicher/Verbuendete). Der Editor-Tab
**"Debuffs & Status"** generiert daraus live ein Lexikon (Debuff-
Familien + verursachende Skills + kind-4-Passiva + Res/Block-Schutz
+ Buff-/Support-Listen).
**OFFIZIELLE AILMENT-WIRKUNGEN (db_tutorial_msg.bin [14], 2026-07-08 —
NICHT raten, das Spiel definiert sie anders als erwartet!):**
Poison = HP-Verlust am Rundenbeginn; Venom = GROSSER HP-Verlust;
Burned = ATK+DEF sinken (KEIN DoT!); Frozen = ACC+EVA sinken (bleibt
handlungsfaehig!); Shocked = nur Move/Attack/Standby (keine Skills);
Held = nur Skill/Standby (kein Move/Angriff, Konter moeglich);
Ice Cell = Frozen+Held; Homonka = Tod bei 2. Nigeki-Kessatsu-Treffer.
Regeln [13]: nur EIN Ailment gleichzeitig (neues ersetzt altes),
heilt nach einigen Runden automatisch. Weitere Tutorial-Perlen:
[15] SKY RIFTS SPAWNEN PERIODISCH HOLLOWS (staerkere mit der Zeit -
relevant fuer die Spawner-Idee!), [16] Bankai braucht hohe S-Pressure,
maximiert SP, SP sinkt pro Runde bis Bankai endet, [5] Bonus-XP nach
Sieg haengt an Rundenzahl/Team-Attacken/Ueberlebenden, [25] Zusatz-
schlaege haengen an S-Pressure + Attribut-Vorteil.
Namen via db_skill_name (Index = Skill-ID), Hilfe via db_skill_help.

### 3.5b db_result.inc — TURM-BELOHNUNGEN (gefunden 2026-07-08)
Eine Zeile pro Etage (1-30, danach Sonderfaelle 100/5xx):
`{etage, BONUSPUNKTE, {8x ?}, {8x FREISCHALT-IDs}, {8x ?}, {8x ?}}`
- Spalte 2 = die nach dem Sieg pro Charakter VERTEILBAREN STAT-PUNKTE
  (User-Fakt: Etage 30 = 50; Tabelle: 19/20/21/23-25 = 10, 26/27 = 20,
  6/12 = 5, 30 = 50 -> passt).
- Gruppe 4 = Charakter-Freischaltungen (Roster-IDs: Etage 6 -> 6 Gin,
  12 -> 44 Tosen, 19 -> 17/53/69 Aizen/Urahara/Yoruichi, 21 -> 181
  Kusaka, 24 -> 118/120 Yammy/Shawlong, 26 -> 114 Ulquiorra,
  27 -> 130 Arturo, 30 -> 116/19 Grimmjow/Aizen2).
- Gruppen 3/5/6: Bedeutung offen (Gruppe 6 evtl. Anzeige/Voraussetzung).
**ARM9-ZWILLING GEFUNDEN (2026-07-08): @ROM 0xF8998, 68-B-Records
{u16 etage, u16 punkte, ...}, Etage n bei BASE+(n-1)*68** - wie bei
db_status/db_btower vermutlich die echte Engine-Quelle. Der Editor-
Workflow patcht bei Aenderungen BEIDE (.inc laengenneutral + ARM9).
**ALLE ETAGEN GEBEN JETZT SKILLPOINTS (2026-07-08):** Etage 1-12 = 5,
13-25 = 10, 26/27 = 20, 28/29/30 = 50 (.inc + ARM9 synchron; vorher
vergebene Werte unveraendert, nur 0-Etagen aufgefuellt; Etage 29 =
kopierter Endkampf bekam 50).
**ROLLEN-BATCHES (PRESET_BATCHES):** "Rolle: Tanks (4)" = Kenpachi/
Komamura/Shinji/Edrad (hoechste HP+DEF), "Rolle: Healer/Support (4)" =
Orihime/Momo/Izuru/Nemu (Heal/Kido-Kits, bewusst KEINE NONCOM!),
"Rolle: Carries/DPS (4)" = Arturo/Aizen/Ikkaku/Hiyori (ATK/HIT/EVA),
"Rolle: Balanced Lobby (12)" = alle drei kombiniert.
**PFAD-AENDERUNG: DeSmuME liegt jetzt in Bleach3P_RE\desmume-0.9.13-
win64\ (User hat den Games-Ordner aufgeloest; DESMUME_EXE/BATTERY_DIR
im Editor angepasst - Battery-Save liegt damit auch dort).**
**iCLOUD-SYNC (2026-07-08, fuers iPhone):** ROM -> `iCloudDrive\Modded
ROM files`, Battery-Save -> `iCloudDrive\Modded DSV files`. Zwei Wege:
(1) Editor spiegelt beim "In ROM speichern" automatisch mit,
(2) Hintergrund-Watcher `tools/icloud_sync.pyw` (Start: "iCloud-Sync
starten.bat" oder automatisch beim Editor-Start; Port-Lock 47653 =
Einzelinstanz, prueft alle 5 s per mtime, kopiert atomar via .tmp).
Damit landen auch reine In-Game-Speicherungen (DeSmuME schreibt die
.dsv) in der iCloud, ohne dass der Editor laeuft.
**ROM-PUSH sicher gemacht (2026-07-08):** Editor-Button "ROM -> Handy
(iCloud)" spiegelt NUR die ROM in `Modded ROM files` (nie den Save).
Auto-Sync beim Speichern + Watcher pushen die ROM immer, die .dsv aber
NUR wenn der PC-Stand neuer ist als der iCloud-Stand -> ein neuerer
HANDY-Save wird nie ueberschrieben.
**RUECKRICHTUNG Handy->PC (2026-07-08):** `tools/icloud_pull.py` holt den
am HANDY gespeicherten .dsv aus `iCloudDrive\Modded DSV files` in den
PC-Battery-Ordner. Drei Ausloeser: Editor-Button "DSV vom Handy holen",
`DSV vom Handy holen.bat` (kann eine Windows-Tastenkombi bekommen), CLI
(`--force`/`--status`). Schutz: Backup des PC-Stands nach
saves/_vom_handy_backup/, und WARNUNG statt Ueberschreiben, wenn der
PC-Stand neuer ist als der Handy-Stand. iPhone-Seite (DeSmuME-.dsv ->
iCloud) = eigenes Shortcut, Anleitung in HANDY-SYNC.md.
**IN-GAME VERIFIZIERT (2026-07-08): Etage 28 = 50 Punkte funktioniert!**
(Skillpoint-Farm: 1-HP-Familiar oneshotten -> 30 Level-XP + 50 Punkte
pro Ueberlebendem. Beide Quellen wurden gepatcht - welche die Engine
liest, ist offen, aber praktisch egal: immer beide patchen.)
XP-Facts (User, in-game): Sieg-XP der Farm = 30 Level-XP (100 XP =
1 Level-Up); Skillpoints kommen NUR aus der result-Tabelle und gehen
an alle UEBERLEBENDEN Chars.

### 3.6 db_btower.inc / ARM9 @0xf3b58
30× `{etage, map_id, party_index}` (party 900+idx, dpos 900+etage).
Etagen→Map: 34,21,6,37,4,20,30,29,14,2,33,31,25,15,39,30,24,10,35,27,17,13,16,34,4,6,25,11,33,31.
Der Editor patcht beim Map-Wechsel BEIDE Quellen (.inc per fs.write, ARM9
per Raw-Write bei `arm9_off(Header@0x20) + 0xf3b58 + (etage-1)*6 + 2`).
Beim Map-Wechsel müssen außerdem die dpos-Subfiles 1–3 (Terrain/Spawn) von
einer Donor-Etage übernommen werden, die die Map original nutzt — sonst
passt die Kollision nicht zur Grafik. Der Editor macht das automatisch
(inkl. Spieler-Startpositionen der Donor-Etage).
**dpos-NARC-Größen: nur 19332 B (Subfile 3 = 1521) oder 19876 B (Subfile 3
= 2067). Maps 27/30/31/35 haben NUR 19876-Donoren** → passen nicht in den
Slot einer 19332-Etage. Fix (2026-07-06): `RomFS.write` zieht zu große
Dateien per Relocation in den freien ROM-Platz um (s. Tool-Tabelle), der
Editor wählt den kleinsten Donor. Damit ist jede Map auf jede Etage legbar.
**Map-Namen:** frei vergebbar über „Map benennen..." (Tower-Tab), gespeichert
in `map_names.json` (nur Editor-Komfort, NICHT in der ROM). Dropdown zeigt
`Map NN - Name  (Etage …)`.
**STORY-MAPS (2026-07-07): 10 neue Maps spielbar — 1, 5, 8 (Free-Battle-
Donoren) + 3, 9, 12, 18, 23, 28, 32 (Story-Kampf-Donoren).**
Technik: `formats.narc_rebuild(template, subfiles)` baut den dpos-NARC
neu (Roundtrip byte-identisch): Subfile 0 + Spawn-Subfile (9288) kommen
von der EIGENEN Etage, Terrain-Grids vom Donor; Deploy-Slots werden
automatisch auf einen begehbaren Cluster gesetzt (Party-Dateien der
Story-/Free-Battles haben ein anderes Format).
Zuordnung Story-Kampf→Map: KEINE Tabelle in ARM9/Overlays gefunden
(ausser der kompilierten db_fbattle @ROM 0xF7DDA, die belegt 226→12);
Rest per VISUELLEM MATCHING verifiziert (Terrain-Grid ueber gerenderte
Map gelegt, Bilder in `dumps/story_map_matching/`): 9→Kampf 99 und
18→220 eindeutig, 3→1, 23→190, 28→229, 32→264 plausibel (in-game
testen!). Map 0 hat KEINEN passenden Donor (einziger Kandidat passte
visuell nicht). ACHTUNG: Maps 3/9/18/23/28/32 sind groesser als das
39x39-Grid — bespielbar ist der Bereich, den auch der Original-
Story-Kampf nutzte. TO-DO-Stand: „TO DO NOTIZEN UND IDEEN/STATUS.md".

### 3.7 db_ability.inc — Typen (Token 1 = kind, Token 5 = Referenz)
kind 1 = Zanpakuto/Waffe (IDs 1–79; 66–74 Bankai-Formen).
kind 2 = **gewährt benutzbaren Battle-Skill**, Token 5 = Skill-ID
(Sai→1, Shakkaho→10, Ginreikojaku→38 — 83 Stück, IDs ~100–134).
kind 3/5/7 = Stat-Passiva, kind 4 = Status-Effekt-Passiva (Token 5 =
Voraussetzung der Upgrade-Kette: Hold 2 ← Hold 1), kind 6 = Bankai,
kind 8 = Shunko, kind 9 = Zenkai, kind 10/11 = Slots, kind 12 = Route End.
**Charakter-Fähigkeitenliste in db_status: Token 0 = eigene Zanpakuto-ID
(1–79, referenziert auch den Level-Up-Pool in db_ability_selection.inc —
nie ändern!), Token 1–9 = Ability-IDs.** Benutzbare Skills gibt man also
über kind-2-Abilities.

### 3.8 Koordinaten (WICHTIG)
Einheiten-/Party-x/y sind **1-basiert**, Terrain-Grid und Karten-Pixel
0-basiert: Einheit (x,y) steht auf Grid-Zelle (x−1, y−1) = Pixel
((x−1)·8, (y−1)·8). Verifiziert: alle 739 Einheiten+Deploy-Slots aller
30 Etagen stehen damit exakt auf Terrain-Wert-10-Feldern.
Terrain-Grid (dpos Subfile 2): 10 = begehbar, 0 = Rand/Deko (NICHT
begehbar), 255 = außerhalb.

### 3.9 Battery-Save (.dsv) — SPIELSTAND-FORMAT (Analyse 2026-07-08)
Ziel: Save-Editor (Live-Party-Stats). Stand:
- .dsv = 64K SRAM + 122-B-DeSmuME-Footer.
- Spielername UTF-16LE @~0x1018/0x401c/0x7020; Datenbloecke a ~0x2900
  bei 0x1000/0x4000/0x7000 (2 Slots + Kopie?) + 0xa000 (System?).
- Charakter-Records: 156-Byte-Stride (klarer Autokorrelations-Peak),
  Feld-Layout UNGEKNACKT (Werte wirken teils gepackt; Blind-Analyse
  ohne Anker nicht eindeutig - Rangiku-Anker Lv20/Exp46 veraltet).
- Diff-Erkenntnisse (Profil 10:58 vs Battery nach Farm-Session, nur
  20 Bytes): AKTIVER In-Game-Slot = Block A (0x1000). @0x100C =
  Save-Zaehler (u8), @0x11BC = Spielzeit (u8 h, u8 m, u8 s),
  @0x3208 = zweiter Zeitstempel, @0x321C = Statistik (u16 Paare,
  z. B. Siege + Gesamt-?), 0x3600er = kleine Zaehler, 0x3792 =
  schrumpfende u16-Liste. @0x4004 u16: sank 0x6A20->0x5B0A -
  KEIN Standard-Checksummen-Match (sum8/16, ~sum, CRC16 IBM/CCITT
  ueber diverse Slot-A-Bereiche) -> evtl. Zaehler, keine Checksumme.
- CHECKSUM-PRAXISTEST LAEUFT: Spielzeit-Stunde @0x11BC 3->4 gepatcht
  OHNE Checksummen-Fix (Backup: saves/_vor_checksum_test.dsv).
  Laedt "Continue" und zeigt ~4h Spielzeit -> KEINE strenge Pruefung,
  Save-Editor kann direkt schreiben. Laedt er nicht/Reset ->
  Checksumme existiert, weiter reversen.
- Slot-A-Charakterdaten: Diff "durchgespielt"(Mai) vs heute schmiert
  ueber 137 Feld-Offsets (2 Monate Fortschritt = zu viel Rauschen) -
  fuer das FELD-Layout weiterhin Kalibrier-Diff noetig (Protokoll in
  TO DO NOTIZEN/STATUS.md), ABER erst Checksum-Frage klaeren.

### 3.10 MOBIL-EDITOR fuers iPhone (2026-07-08)
`iphone_editor.py` = EINE eigenstaendige Datei (kein tools/ noetig), laeuft
in iOS-Python-Apps (Pyto/a-Shell/Pythonista) und auf dem PC. Menuegesteuert
(input()): Etage anzeigen / randomisieren (Level+Anzahl, begehbar, Blick
zur Deploy-Zone, Sprite-Limit 25, Riesen/NONCOM/Blacklist raus) /
Skillpoints setzen (db_result + ARM9-Zwilling @0xF8998) / GOD-MODE.
Inlined: NDS-Header/FNT/FAT, RomFS(+Relocation), NARC, dpos read/pack,
party_slots, VERIFIED_POOL. ROM-Pfad wird auto-gesucht (iCloud/Skript-
Ordner) oder oben ROM_PATH setzen. Der tkinter-PC-Editor laeuft NICHT auf
iOS - der Mobil-Editor deckt die schnellen Aktionen ab. Anleitung:
HANDY-EDITOR.md. Auf PC verifiziert (anzeigen/randomisieren/Skillpoints).

## 4. Toolkit (`tools/`)

| Datei | Funktion |
|---|---|
| `romfs.py` | NitroFS lesen; `RomFS.write(pfad, daten, out_rom)` patcht in-place (Datei ≤ Original; kleiner → FAT-Ende angepasst; **GRÖSSER → Relocation** in freien ROM-Platz ab `max(FAT-Ende)` ≈ 0x78E8A14, ~7 MB 0xFF; FAT-Start+Ende + Header-„used size" @0x80 angepasst). `out_rom` erzeugt/patcht Kopie. |
| `formats.py` | BGSM, NARC, `.inc`-Parser (`parse_inc`) |
| `faces.py` | Huffman-Decoder, NCGR/NCLR, `face_png()` |
| `fmap.py` | Karten-Renderer, `MAP_TABLE`, `map_png(fs, map_id)` |
| `tower.py` | `floor_units/pack_units`, `party_slots/pack_party`, CLI: `dump` / `build floors.json [out.nds]` |
| `characters.py` | erzeugt die CSV-Dumps neu |
| `bgsm.py`-Äquivalent | in formats.py enthalten |

`stat_editor.py` = GUI (4 Bereiche: Charaktere mit Porträts/Stats/Pressure,
Bleach Tower mit klickbarer Karte, Skills & Fähigkeiten, Crash-Schutz).
Speichert wahlweise in Kopie (`Bleach3P modded.nds`) oder Original.

## 5. Dumps (`dumps/`)

- `characters.csv` — 255 Einheiten mit allen Werten (Spaltennamen z. T. alt: spi/spd = HIT/EVA)
- `names.csv` (371), `abilities.csv` (513) — ID↔Name
- `tower_dump.txt` / `tower_floors.json` — alle 30 Etagen (Text / editierbar für tower.py build)
- `maps/etage_NN_mapXXX.png` — alle 30 Etagen-Karten, rot = Gegner, blau = Deploy
- **`vanilla_ref.json`** — WICHTIG: Vanilla-Slot-Templates aller 30 Etagen
  (nur initial platzierte Slots: slot/active/raw) + Vanilla-Basisstats
  aller 255 Einheiten. Wird vom Randomizer (Etagen-Limit) und vom
  Stat-Boost (idempotente Basis) benutzt. Bei Bedarf neu erzeugbar aus
  Bleach3P_test_mod.nds.

## 6. Offene Punkte / nächste Schritte

1. ~~Map-Wechsel testen~~ **ERLEDIGT: in-game verifiziert** (Etage 1 auf
   Hafenstadt-Map 21 umgestellt — Grafik UND Kollision korrekt).
2. **Klon-Einheiten (User-Wunsch: Captains/Ichigo als skalierende Gegner):**
   Erster Versuch (Kenpachi-Daten auf freie Unit 2: db_status-Zeile,
   db_growt-Zeile, s_name-Zeiger umgebogen, dpos-Spawn) → CRASH beim
   Kampfstart, komplett zurückgerollt. Ursache ungeklärt: entweder die
   damals nötige globale Whitespace-Schrumpfung der .inc (heute irrelevant,
   ARM9 ist die Wahrheit) ODER eine weitere pro-Unit indizierte Tabelle,
   die für Unit 2 leer ist. RETRY-PLAN: Klon NUR in die ARM9-Stat-Tabelle
   schreiben (Record von Unit 2 mit Kenpachi-Daten füllen, typ=6) und
   bisektieren: erst nur Daten (nicht spawnen) → bootet? Dann spawnen.
   Kandidaten für weitere pro-Unit-Tabellen: ARM9-Growth @0x105E84+unit·76
   (aus Vorgänger-Projekt bekannt, HIER noch unverifiziert), db_partner,
   db_f_partner, db_growt.
3. **Gegner-AI:** raw[1]/raw[2] (AI-Typ/Aggro) sind einstellbar, aber die
   Bedeutung der AI-Typ-Werte (0,1,3 gesehen; alt auch 5,6,12,15) und der
   restlichen raw-Felder (raw[3] 1/2, raw[10] 256/512-Flags) ist unkartiert.
   „Aggressiv"=3/100 ist Vanilla-Muster, in-game-Wirkung noch zu bestätigen.
3a2. **ZWILLINGE & ZENKAI (2026-07-08):** Zenkai-Kette = 242->243->244
   (kind 9, Upgrades + ZK Length 269-271 im Skill-Tree-Pool von SET 48 =
   erweckte Waffe des MAIN-Twins). Side-Twin bleibt auf Set 50/11
   (Ryujomaru/Fujimaru bzw. Kotomaru/Matsuri; Set 11 hat KEINEN Pool ->
   darum kein Bankai fuer Side-Matsuri). Spielbare Twin-Units: Fujimaru
   21/22, Matsuri 26/27 (je person 21/26, beide MIT _b-Sprite!); 23/28 =
   ausgebaute Story-/Gegner-Versionen. EXPERIMENT LAEUFT: Zenkai 1 (242)
   in die ARM9-Ability-Listen von Unit 26+27 geschrieben -> testet, ob
   Side-Matsuri als Spieler-Char den Verwandlungs-Befehl bekommt
   (S-Pressure voll aufladen!). Fujimarus Bankai-Kette = 245-247
   (Pool von Set 50 lehrt 246/247), NICHT Ikkakus wie frueher vermerkt.
3b0. **BANKAI-GEGNER: DATENSEITIG ABSCHLIESSEND WIDERLEGT (2026-07-08).**
   Vollstaendige Testreihe auf Etage 3 (alles zurueckgerollt):
   (a) Persoenliche VS-AI-Typen (Byakuya 11, Kenpachi 12, Hitsugaya 2,
       Komamura 16, Mayuri 7, Grimmjow 15, Ichigo 12, Renji 19) +
       Aggro 100 -> kein Bankai, kein gezieltes Aufladen.
   (b) + S-Pressure-Start 100 (ARM9 +26) -> Bar spawnt NICHT voll
       (+26 ist also KEIN Startwert fuer Turm-Gegner - Bedeutung offen).
   (c) + Tail-Bytes + Tabellen-Stats 7000 HP -> Stats werden ABSURD
       (Engine nimmt Tabelle als Lv1-BASIS und waechst auf dpos-Level
       hoch! Tail-Trick ist nur bei Lv-1-Einheiten sicher, s. XP-Farm),
       Bar weiterhin nicht voll, und SELBST MIT MANUELL VOLL GELADENER
       Bar ueber mehrere Zuege zuendet KEIN Gegner Bankai.
   VS-Vergleich: auch db_VSstatus.inc gibt Captains nur Pressure 19-39;
   in den Challenges laden sie via Angriffe und zuenden per AI/Engine.
   FAZIT: Der Bankai-Trigger fuer Gegner haengt an Kampf-CODE (ARM9/
   Overlay, evtl. Story-Event-gebunden) - nur noch per Code-RE loesbar
   (_b-Sprite-Ladelogik als Einstieg).
   **ARM9-CODE-RE (2026-07-08, capstone; ARM9 laedt bei RAM 0x02000000,
   ROM-Offset = RAM-0x02000000+0x4000):**
   - Sprite-Loader (ARM-Mode) @0x2050C40: `%s%03d`-Filename-Builder.
     Entscheidung `_b.bin` vs `.bin` @0x2050C5C:
     `ldr r0,[r8,#0x50]; tst r0,#8; beq normal` -> BIT 3 von [ctx+0x50]
     = optischer Bankai-Zustand.
   - Wer setzt [ctx+0x50] Bit 3? Funktion @0x205AAC8 (Sprite-Refresh):
     @0x205AB88 `and r0,[unit+0x10],#0x40000; cmp; bne` -> setzt das
     Sprite-Bit NUR wenn **[unit+0x10] BIT 18 (0x40000) = das echte
     Bankai-Zustandsflag der Einheit**.
   - 0x40000 wird an 81 Code-Stellen getestet/gesetzt; kompakte SETTER
     (Aktivierungs-Kandidaten): @0x205904C (`[r6+0xc] |= 0x40000`, daneben
     @0x205903C `|= 0x10000` = Paar), @0x2055D14, @0x2091008. Struct-Offset
     variiert (0xc vs 0x10) -> mehrere Structs, muss dynamisch aufgeloest
     werden.
   STATUS: **GEPARKT/AUFGEGEBEN (2026-07-08).** Mechanik-Kette statisch
   kartiert (Flag [unit+0x10]&0x40000 -> Sprite-Bit [ctx+0x50]&8), aber
   die Aktivierung + Gate liessen sich statisch nicht eindeutig aufloesen
   (81 Nutzungen von 0x40000, mehrere Struct-Offsets). Der einzige sichere
   Abschlussweg waere dynamisches Debugging (Execute-Breakpoints in
   DeSmuME) - vom USER ABGELEHNT (schon frueher getestet, nie erfolgreich,
   extrem zeitaufwaendig). Adressen oben bleiben als Notiz, falls jemand
   spaeter mit anderem Toolset (z. B. Ghidra + Emu-Trace) rangeht.
   ENDGUELTIGES FAZIT: Bankai-Gegner sind mit vertretbarem Aufwand NICHT
   machbar - Thema abgeschlossen.
3b. **Bankai-Gegner (User-Wunsch: Gegner starten im Bankai) — 2 FEHLVERSUCHE
   (2026-07-03), NICHT wiederholen:**
   (a) Zanpakuto-Set-ID (Faehigkeiten-Slot 0) auf die Bankai-Waffe 66-74
       getauscht (Byakuya→68 usw.): spawnt NORMAL, kein Bankai-Zustand.
   (b) S-Pressure-Startwert (ARM9 +26) auf 100 + aggressive AI (3/100):
       AI zuendet ihr Bankai trotzdem nicht.
   Beide Aenderungen wurden komplett zurueckgerollt (Vanilla-Stand).
   FAKTEN dazu: Turm-Captains haben ihre "Bankai 1"-Ability (kind 6:
   227 Byakuya, 230 Renji, 233 Komamura, 239 Hitsugaya, 245 Ikkaku,
   248 Mayuri, 254 Ichigo, 257 Release Grimmjow, 242 Zenkai Kenpachi)
   bereits in der Faehigkeitenliste; 14 person-IDs haben _b-Bankai-Sprites
   (8,21,26,32,33,36,43,46,48,50,55,94,115,129). NAECHSTE ANSAETZE:
   AI-Typ-Werte durchprobieren (raw[1]=15 war im Vorgaenger-Projekt
   Boss-AI), dpos-raw-Restfelder auf ein "Start-Zustand"-Flag testen,
   oder die _b-AI-Skripte im ROM suchen (Bankai-Trigger-Logik).
4. Bedeutung der X-Blöcke in dpos-Subfile 1 (AI-Gruppen?) und von
   Subfile 3 (NICHT Deploy-Zone) offen.
5. Spalten unk14–17/20/22/23 in db_status, db_ability.inc-Restspalten,
   db_growt-Restspalten: Bedeutung offen.
6. **Verdacht: db_skill.inc ist wie db_status ein Build-Artefakt** — wenn
   Skill-Kosten-Edits in-game nichts bewirken, die kompilierte Skill-
   Tabelle im ARM9 suchen (gleiches Muster wie Stat-Tabelle).
7. Huffman-**Packer** fehlt (für Porträt-/Karten-Mods nötig).
8. ~~CRI-CPK nicht dekodiert~~ **GEKNACKT (2026-07-08): `tools/cpk.py`**
   parst ITOC-CPKs (@UTF big-endian) + CRILAYLA-Dekompressor (Magic ist
   hier AUSGENULLT: 8x00 statt "CRILAYLA", dann u32 uncomp/comp; letzte
   0x100 B der Datei = Raw-Praefix des Originals). Befunde:
   `/yamada/FIcon/tex.cpk` = 123 CHARAKTER-KOPF-ICONS 32x32 (linear 4bpp
   NARC[RGCN+RLCN], Datei-ID = person*10 + Variante, inkl. Bankai!),
   `/kuro/cmn/cmn.cpk` = Battle-Animations-Sprites,
   `/kuro/g/C_type000` = Power/Tech/Speed/NonCom-Badges.
   Per-Skill-Icon-Sheet NICHT gefunden (Skill-Screen zeichnet nur Text;
   sys_skill.narc = Menue-Skin). map.cpk jetzt dekodierbar (ungetestet).

## 7. Verifikationsstand

- dpos/party: Round-Trip aller 30 Etagen byte-identisch.
- **IN-GAME VERIFIZIERT (DeSmuME, 2026-07-02):** Randomizer-Gegner spawnen
  auf Gegnerseite (Team 3) mit korrekten Positionen; Team 1 spawnt als
  Player-Team; typ=1-Roster-Chars ziehen Save-Stats (Rangiku Lv20 statt 78);
  „Whole" (177) ist in-game kaputt.
- Patches (Stats, Skills, Turm-Einheiten, Deploy-Slots, btower .inc+ARM9)
  in Test-ROMs geschrieben und korrekt zurückgelesen (E2E im Selbsttest).
- Karten-Rendering visuell verifiziert (MAP181 Hafenstadt, MAP291 Ödland,
  MAP381 Waldlabyrinth); Zellgröße 8 px + 1-basierte Einheiten-Koordinaten
  über Terrain-Grid-Abgleich (739/739 Treffer) bewiesen.
- GUI-Selbsttest: `python stat_editor.py --selftest` → „SELFTEST OK".

## 8. Setup/Workflow (Stand 2026-07-03)

- **Arbeits-ROM:** `Bleach3P_RE\Bleach3P modded.nds` — Editor lädt und
  speichert sie standardmäßig DIREKT (ein-ROM-Workflow, DEFAULT_ROM in
  `tools/romfs.py`). `Bleach3P_test_mod.nds` daneben = QUASI-VANILLA-
  REFERENZ (nur Etage-1-Slot-16 = Menos Lv50 geändert) — NICHT anfassen,
  sie ist die Quelle für vanilla_ref.json, Wiederherstellungen und Diffs!
- **Spielstand:** `Desktop\Games\Bleach 3rd Phantom\desmume-0.9.13-win64\
  Battery\Bleach3P modded.dsv` (durchgespieltes Savegame, Charaktername
  „Kudo Fujimaru" → Bleach Tower sofort zugänglich). Battery-Saves sind an
  den ROM-DATEINAMEN gebunden, zwischen ROMs portabel (Kopie reicht).
- **Emulator:** DeSmuME 0.9.13 im selben Games-Ordner. Editor-Kopfzeile hat
  einen „DeSmuME starten"-Button; nach jedem Speichern startet DeSmuME
  automatisch neu mit der Ziel-ROM (Checkbox; beendet vorher laufende
  Instanzen, da DeSmuME sonst den alten ROM-Stand aus dem RAM spielt).
- **Save-Manager** (Button in der Kopfzeile): beliebig viele Spielstand-
  Profile als .dsv-Kopien in `Bleach3P_RE/saves/` (Profil „durchgespielt"
  = der fertige Save als sichere Basis). Profil laden beendet DeSmuME,
  sichert den aktuellen Stand automatisch als „_vorher" und setzt die
  Kopie als aktives Battery-Save. Ersetzt den fehlenden 3. Save-Slot —
  ein echter 3. Slot im Spielmenue sowie eine Etage 31 wurden geprueft
  und verworfen (btower-Tabelle hat Terminator + direkt anschliessende
  Daten, dpos_931 fehlt, Menu-/Progress-Code hartkodiert; s. Abschnitt 6).
- **Editor-Architektur (WICHTIG fuer Weiterentwicklung):** Die ARM9-Stat-
  Tabelle ist in BEIDE Richtungen die Wahrheit: `_load_arm9_into_model`
  ueberschreibt beim Laden das .inc-Zeilenmodell mit den ARM9-Records,
  `_sync_arm9_status` schreibt beim Speichern zurueck. Der db_status.inc-
  Write ist nur noch best-effort (wird bei Platzmangel still uebersprungen
  — die Datei ist ein Build-Artefakt, die Engine liest sie nicht).
- **Editor-Features:**
  - Charaktere: Stats/Equip editieren, Skill-Picker mit ZWEI Tabs
    (benutzbare Skills kind=2 mit Skill-Anzeige / passive Faehigkeiten),
    Live-Vorschau AKTIV|passiv, Crash-Schutz (nur 195 sichere Einheiten).
  - Char-Designer (eigener Tab): Pool-Charakter waehlen -> umbenennen
    (s_name.bin + _fre werden via bgsm_replace_strings neu gepackt,
    identische Strings teilen sich einen Eintrag = Groesse bleibt),
    Stats (Lv/HP/SP/ATK/DEF/HIT/EVA/MOV/S-Pressure) und Faehigkeiten
    setzen ("Skills waehlen..." nutzt denselben Picker mit var-Param),
    "Design speichern" schreibt in .inc+ARM9 (dirty_status) + dirty_names,
    "In aktuelle Etage einsetzen" platziert als Team-3-Gegner mit
    aggressiver AI auf freier begehbarer Zelle (Sprite-Limit-Check).
    Aenderungen gelten GLOBAL fuer den Charakter (ARM9). ACHTUNG:
    Randomizer wuerfelt Skills neu -> designte Gegner nicht mehr
    randomisieren. Umbenennungen landen bei "In ROM speichern" in
    s_name.bin (ATK/DEF/HIT/EVA/MOV sind u8 -> max 255, hart geprueft).
  - Bleach Tower: klickbare Karte (skaliert mit dem Fenster, Mausrad-
    Scroll, gruene Punkte = begehbar, rot = Gegner, tuerkis = Team 1,
    blau = Deploy), Einheiten-Editor (char/level/x/y/dir/ai/aggro/team),
    Map-Wechsel-Dropdown (Donor-Terrain wird mitkopiert), Deploy-Slots.
    Copy/Paste: "Kopieren" legt die gewaehlte Einheit ins Clipboard,
    "Einfuegen" dupliziert sie auf der aktuellen Etage (gleiche Werte
    char/level/dir/team/ai/raw, neuer Slot + freie begehbare Zelle,
    Sprite-Limit-Check nur bei neuem Char). Ideal, um eine Entity
    mehrfach zu platzieren.
    Button "AI-Skills...": editiert die Subfile-1-Skill-Liste der gewaehlten
    Gegner-Einheit (welche Battle-Skills die AI im Kampf einsetzt; Passiva
    des Original-Blocks bleiben erhalten). Block-Index = Position der Einheit
    in Slot-Reihenfolge; Aenderung landet in self.ai_base[floor] und wird
    beim Speichern als NARC-Basis mitgeschrieben. tools/tower.py:
    ai_block_count/ai_block/set_ai_block (Blockgroesse 36 u16 bleibt).
    Button "Skills/Faehigkeiten...": springt fuer den gewaehlten Gegner
    zum Skill-Picker und uebernimmt bei OK direkt (auto_apply) - ACHTUNG:
    Faehigkeiten haengen am CHARAKTER (ARM9), gelten also ueberall wo er
    auftaucht, und der Randomizer wuerfelt Loadouts neu (Skills erst
    NACH dem Randomisieren vergeben).
    PRESET-BATCHES (PRESET_BATCHES in stat_editor.py): thematische
    Gegner-Gruppen per Dropdown+Button im Randomizer-Bereich einsetzbar
    (Captains, Bankai-Chars, Arrancar/Espada, Vize-Captains, Hollows,
    Aizen & Verraeter, Ichigo & Freunde, Zanpakuto-Wesen, Mobs) -
    nutzt Ziel-Level/Verhalten/Boosts des Randomizers, gekappt auf
    Etagen-/25er-Limit, nur verifizierte Pool-IDs, keine Riesen.
  - Randomizer-Extras (2026-07-07): Batch-Filter ("nur aus" / "ohne"
    Preset-Batch), Challenge-Dropdown ("Gegner spawnen bei den
    Teammates" = nur die naechsten Zellen ums Deploy-Zentrum),
    Button "ALLE 30 Etagen randomisieren" (Challenge-Run mit den
    aktuellen Einstellungen). Char-Designer-Button "ALLE Chars:
    Slots auf 9 auffuellen" (leere Ability-Slots -> Zufalls-Passiva,
    Wirkung bei spielbaren Chars in-game ungetestet).
  - Randomizer: Level = Ziel +-5 (UNGEBOOSTET, User-Klarstellung);
    NUR die Stats kriegen den globalen x1.25-Boost:
    Faktor (1+Lv/100)x1.25, z. B. Ziel 80 -> x2.25
    (LEVEL_STAT_SCALE in stat_editor.py, User-Wunsch 2026-07-06).
    AUSREISSER-DAEMPFUNG (ATK/DEF/HIT/EVA, stetig): Anteil bis
    1.3x Pool-Schnitt (OUTLIER_THRESH) skaliert voll, Ueberschuss
    darueber nur x1.1 (OUTLIER_SCALE) - verhindert EVA/ACC 95+
    (Yoruichi-Problem). HP/SP skalieren immer voll. Beispiel Lv80:
    Yoruichi EVA 29 -> 51 statt 65, Kenpachi ATK 37 -> 62 statt 83.
    Anzahl min-max (Cap = MAX_UNIQUE_SPRITES=25, Extra-Slots werden
    angehaengt), Verhalten Original/Aggressiv/Defensiv, Riesen-Sprites
    (BIG_UNITS) ausgeschlossen, Blickrichtung zum Deploy-Zentrum,
    jeder Char kriegt 5 Zufalls-Skills + 4 Passiva.
    GOD-MODE-Button: Lv 91-99 (ungeboostet) + HPx3.75/Restx2.5.
  - Design: modernes Dark-Theme (Schwarz #111318 + Ichigo-Orange #ff7a1a,
    Bahnschrift-Headlines; Konstanten G_* oben in stat_editor.py).
- **Selbsttest nach JEDER Code-Aenderung ausfuehren:**
  `python stat_editor.py --selftest` (prueft auch Pool-Regeln, Randomizer-
  Invarianten, ARM9-Sync E2E auf einer Wegwerf-Kopie).

## 9. Chronik der geloesten Probleme (Lehren, NICHT wiederholen!)

Alle in-game auf DeSmuME verifiziert (2026-07-02/03):

1. **Marker einen Tile daneben** → Einheiten-Koordinaten sind 1-basiert,
   Grid/Pixel 0-basiert (739/739-Beweis). Editor ueberall gefixt.
2. **Randomizer-Gegner spawnten im Spieler-Team** → dpos-Byte 1 ist das
   TEAM (3=Gegner, 1=Spieler, 5=Spezial), kein „aktiv"-Flag.
3. **Gegner stark unterlevelt (Rangiku Lv20 statt 78, Shinji normal)** →
   Roster-verknuepfte Charaktere ziehen Save-Stats. Erkennung: typ=1 ODER
   db_partner.inc-Flag=1. Pool doppelt gefiltert.
4. **„Whole" (177) kaputt gespawnt** → RANDOMIZER_BLACKLIST (176/177/185).
5. **Stat-Boosts wirkten in-game nicht** → db_status.inc ist Build-
   Artefakt; Engine liest NUR die ARM9-Tabelle @0x101C52+(unit−15)·70.
   Editor synct jetzt beidseitig.
6. **„db_status.inc wird zu gross"-Fehler** → .inc-Write ist best-effort;
   ARM9 ist massgeblich. Fehler kann nicht mehr auftreten.
6b. **„db_btower.inc wird zu gross" beim Map-Wechsel** (2026-07-06) →
   Map-ID mit mehr Ziffern (z. B. 6→34) verlaengert die .inc-Zeile, Datei
   hat keinen Puffer. Fix: _patch_btower kompaktiert erst Leerzeichen
   (`, `→`,`, reicht fast immer), sonst wird der .inc-Write UEBERSPRUNGEN
   und nur die ARM9-Tabelle @0xf3b58 gepatcht (die massgebliche Quelle,
   wie bei db_status). Bricht den Speichervorgang nicht mehr ab.
7. **Crash bei GOD-MODE 30 Gegner Etage 14** → ZWEI Ursachen bisektiert:
   (a) zu viele UNIQUE Sprites (23; DS-RAM-Limit ~16) → Cap, inzwischen
   14 unique in-game verifiziert;
   (b) mehr Gegner als die Etage original initial platziert → Randomizer
   nutzt exakt die Vanilla-Slot-Templates (vanilla_ref.json).
8. **Kenpachi-Klon auf Unit 2 → Crash** → zurueckgerollt; Retry-Plan in
   Abschnitt 6.2. Lehre: .inc-Dateien NIE global umformatieren; Aenderungen
   einzeln in-game testen (bisektieren!), test_mod.nds als Restore-Quelle.
9. **Boosts stapelten sich ueber Sessions (Shinji x4 ATK)** → Boosts
   rechnen jetzt immer von den Vanilla-Basiswerten (vanilla_ref.json).
11. **AI-Endlos-Zuege: Yachiru griff auf Etage 2 ohne Ende an** (in-game
   2026-07-07) → Ursache: Zufalls-Passiv **375 "Hit & Run"** ("Enable
   movement after attacking") - die aggressive AI kettet Angriff->Zug->
   Angriff bis zum Tod. Fix: AI_ABUSE_PASSIVES = {375} ist aus den
   Zufalls-Loadouts raus (manuell zuweisbar; auf Spieler-Chars sehr
   stark). Merke: kind-5-Passiva koennen AI-Verhalten aushebeln.
10. **CRASH: Female Spirit (251) toetete Spieler-Char, fuehrte "Pressure"
   aus → Spiel-Crash (in-game 2026-07-06, Etage 2).** Ursache: NONCOM-
   Kampftypen (db_status Attribut/Spalte 13 = 0 oder 4: Healer/Zivilisten
   wie Female Spirit, Unohana, Hanataro, Tatsuki, Rukon-Leute, Minazuki,
   Konoka, Shiyo) haben keine vollstaendigen Angriffs-/Pressure-Daten -
   normale Angriffe/Zusatzschlaege koennen crashen; nur Skills sind
   sicher. Da die AI-Aktionswahl nicht steuerbar ist (raw-Felder
   unkartiert): noncom_units werden aus Randomizer UND Preset-Batches
   ausgeschlossen (Captains-Batch daher ohne Unohana!), manuelles
   Platzieren zeigt eine Warnung. Batch-Verifikation prueft nur
   Spawn/Level, NICHT Kampfaktionen - weitere solche Faelle moeglich.

## 10. Quickstart fuer den naechsten Chat

1. Ordner: `Desktop\Bleach3P_RE\`. ERST diese Datei (REPORT.md) und
   README.md lesen — sie sind der komplette Wissensstand.
2. Editor: Doppelklick `Editor starten.bat` (laedt Bleach3P modded.nds).
   Test-Zyklus: aendern → „Alle Aenderungen in ROM speichern" → DeSmuME
   startet automatisch → im Spiel „Continue" → Bleach Tower.
3. Aktueller ROM-Zustand (Bleach3P modded.nds, Ende 2026-07-03):
   - Etage 1: 25 Gegner Lv45 (10 Captains, Izuru, Hanataro, Aizen,
     Kaien, Momo, Renji, Hisagi, Rangiku 209, Yachiru, Ikkaku,
     Yumichika, 2x Urahara, Nemu, Rukia; Slots 16-40) — das ist der
     VERIFIZIERTE 25er-Limit-Test, laeuft sauber. Etage weiter auf
     Map 21 (Hafenstadt).
     Etage weiter auf Map 21; Positionen aus dem aktuellen Terrain-
     Grid, nicht auf/neben Deploy-Slots. Aufbau-Skript (Scratchpad,
     N als Argument): waehlt N Pool-Chars mit N verschiedenen
     person-IDs, prueft Sprite-Existenz, Ruecklese-Check.
   - Etage 14: 8 Zufalls-Gegner Lv91-98 auf Vanilla-Slots (Bisect-Test)
   - Etage 26: 17 Zufalls-Gegner Lv75-85 (Team nachtraeglich auf 3 gefixt)
   - ~35 Pool-Charaktere haben geboostete Stats im ARM9 (z. T. doppelt
     geboostet, Caps griffen); Faehigkeiten aller Chars = VANILLA.
     Naechstes Randomisieren setzt saubere Werte von Vanilla-Basis
     (vanilla_ref.json). Bankai-Experiment-Aenderungen (Set-IDs,
     S-Pressure) sind komplett zurueckgerollt.
   - Etage 29 = KOMPLETTE KOPIE der Vanilla-Etage 30 (2026-07-08):
     dpos_930 (19876 B, per Relocation in freien ROM-Platz) + party_930
     + Map 31 (ARM9-btower + .inc gepatcht). Der originale Endkampf
     ist also auf Etage 29 spielbar.
   - Etage 30: XP-FARM-VERSUCH KOMPLETT ZURUECKGEROLLT (2026-07-08,
     Etage wieder VANILLA; db_result-Bonus wieder 50; Familiar 151
     wieder Vanilla-Stats; Blacklist-Aenderung entfernt). GRUND:
     Nach dem Toeten des einzelnen Familiars CRASHTE das Spiel UND
     DeSmuME komplett. Verdaechtige (ungeklaert): (a) db_result-99-
     Patch, (b) Sieg-Sequenz von Etage 30 (Endcredits?) mit Nicht-
     Vanilla-Aufbau, (c) 1-Gegner-Aufbau auf Etage 30 selbst.
     User baut die Farm kuenftig SELBST im Editor (Lv1-Mob, 1 HP).
     ERKENNTNISSE aus dem Versuch: (1) In-game-Gegner-HP/DEF werden
     NICHT roh aus der ARM9-Statustabelle gelesen (Basis-HP 1 -> Anzeige
     3480, DEF 40; ATK/ACC/EVA dagegen roh). URSACHE GEKLAERT (2026-07-08):
     die GROWTH-TAIL-BYTES! ARM9-Growth-Tabelle @0x105E84 + unit*76 ist
     fuer diese ROM BESTAETIGT (Key-Echo @+0). Tail-Bytes @+68..+75:
     nonzero (z.B. 01 01 0a 0a 0a 0a 0a 00 bei Spielbaren) -> Turm liest
     HP/DEF aus der STAT-TABELLE; alles null (alle Gegner) -> Turm
     BERECHNET HP/DEF ueber die Wachstumsformel und ignoriert die
     Stat-Tabelle. Fix fuer 1-HP-Dummies: Tail-Bytes setzen.
     (2) Etage-29-Kopie der Vanilla-Etage-30 blieb bestehen.
   - Etage 28 = XP-FARM v2 (2026-07-08, nach Tail-Byte-Fix): 1 Familiar
     (151) Lv1 bei (23,23) neben Deploy-Zentrum (26,23), defensiv;
     151-Stat-Tabelle HP=1/SP=2/Rest=1, Tail-Bytes gesetzt, 151 wieder
     in RANDOMIZER_BLACKLIST (Pool 110). Sky Rift + alle Vanilla-Gegner
     der Etage entfernt (Sieg = alle besiegen). IN-GAME ZU TESTEN:
     zeigt der Familiar jetzt 1 HP? Crasht der Kill hier NICHT (dann
     war der Etage-30-Crash die Sieg-/Credits-Sequenz)?
     Achtung lt. db_result: Etage 28 gibt 0 BONUSPUNKTE (26/27 = 20!),
     nur normale Sieg-XP.
   - Etagen 11-15 = EIGENE KAMPAGNE "Der Riss ueber Karakura"
     (2026-07-08, s. CUSTOM_CAMPAIGN.md): F11 6 Hollows Lv15, F12
     9 Vize-Captains Lv30 (Nemu heilt), F13 3 Captains+Hollows Lv45
     (Byakuya Kidoh, Hitsugaya Eis), F14 11 Arrancar Lv60 (Cero-Garde
     + Nemu-Heiler), F15 Boss Arturo(129) Lv95 GOD-Stats + 5 Elite
     Lv90. AI-Skills je Gegner via set_ai_block gesetzt. In-game noch
     zu balancen.
   - Uebrige Etagen: vanilla.
   - Editor-Pool: VERIFIED_POOL_IDS = 111 einzeln verifizierte Gegner
     (Batch-Tests 1-10); Save-Manager-Profil "durchgespielt" in saves/.
4. User-Ziele (Stand jetzt): eigene Level bauen (Etagen ersetzen statt
   neue erstellen), Randomizer mit Leveln 80/90+, uebertriebene Gegner
   (GOD-MODE), Map-Wechsel testen, Klon-Gegner (Captains als skalierende
   Gegner) — Retry gemaess Abschnitt 6.2. Kommunikation: informelles
   Deutsch, testet selbst schnell in DeSmuME und meldet Ergebnisse.
