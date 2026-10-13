# Bleach: The 3rd Phantom (EU) — Reverse-Engineering-Toolkit

ROM: `C:\Users\danie\Downloads\Bleach - The 3rd Phantom (Europe) (EnFr)\...nds`
(Header: `BLEACH 3RD`, Gamecode `YBTP`, ARM9 unkomprimiert, 6126 Dateien im NitroFS)

## Wo liegt was in der ROM

| Pfad | Inhalt |
|---|---|
| `/yamada/DataBase/db_btower.inc` | **Bleach Tower**: 30 Zeilen `{Etage, MapNr, PartyIndex}` (Klartext!) |
| `/yamada/DataBase/db_dpos_9NN.narc` | Einheiten der Turm-Etage NN (901–930) |
| `/yamada/DataBase/db_party_9NN.narc` | Spieler-Deployment-Slots der Etage |
| `/yamada/DataBase/db_dpos_XXX.narc` | dito für Story-Kämpfe (000–264), Free Battle (8XX), VS (7XX/5XX) |
| `/yamada/DataBase/db_fbattle.inc` | Free-Battle-Liste `{Nr, StoryRef, PartyId, MapNr, GegnerLevel}` |
| `/yamada/DataBase/db_status.inc` | **Charakter-Basiswerte** (255 Einheiten, Klartext) |
| `/yamada/DataBase/db_growt.inc` | Level-Up-Wachstumsraten |
| `/yamada/DataBase/db_ability.inc` | Fähigkeiten-Definitionen |
| `/yamada/DataBase/db_item*.bin` | Items (BGSM-Text) |
| `/yamada/ScrDat/s_name.bin` | **Namenstabelle** — Index = Charakter-ID (371 Einträge) |
| `/yamada/FMap/MAPxxx.bin` | Schlachtfeld-Karten (Grid/Tiles) |
| `/yamada/DataBase/db_victory.bin` | Siegbedingungs-Texte pro Kampf |

**Wichtig:** Die `.inc`-Dateien sind Klartext (C-Initializer), die die Engine
zur Laufzeit parst — mit jedem Texteditor änderbar, solange die Datei nicht
größer wird als das Original (der Patcher polstert kleinere Dateien mit Nullen).

## Format db_dpos (Einheiten eines Kampfes)

NARC mit 4 Subfiles. Subfile 0 = Einheiten-Records à **54 Bytes**:

| Offset | Typ | Bedeutung |
|---|---|---|
| 0 | u8 | Slot-Nr (1-basiert) |
| 1 | u8 | **TEAM**: 3 = Gegnerseite (ALLE Turm-Gegner!), 1 = Spielerseite. In-Game-verifiziert: mit 1 spawnen Einheiten im Player-Team |
| 2 | u16 | Charakter-ID (→ `dumps/names.csv`) |
| 4 | u16 | Level |
| 6 | u16 | unbekannt (immer 10) |
| 8/10 | u16 | X / Y auf dem Grid — **1-basiert!** Zelle im 0-basierten Terrain-Grid = (X−1, Y−1) |
| 12 | u16 | Blickrichtung: 0=Ost/+x, 1=Nord/−y, 2=West/−x, 3=Süd/+y (aus Vanilla-Statistik abgeleitet) |
| 14 | u16 | unbekannt (immer 1) |
| 16+ | u16[19] | AI/Extras (beim Editieren unverändert lassen) |

Turm-Etagen: Slots 1–15 = Spieler-/Reserve-Slots, ab Slot 16 = Gegner.
Subfile 1 = **AI-Skill-Listen pro Einheit** (ein 36-u16-Block je Record in
Slot-Reihenfolge = der Skill-/Fähigkeits-Pool, aus dem die Gegner-AI wählt;
geknackt 2026-07-08), Subfile 2 = 39×39-**Terrain-Grid**
(`10` = begehbar, `0` = Rand/Deko — NICHT begehbar, `255` = außerhalb),
Subfile 3 = 39×39-Grid unklarer Bedeutung (kein Deploy-Zonen-Grid).
Verifiziert: mit 1-basierten Koordinaten stehen ALLE 739 Einheiten/Deploy-Slots
aller 30 Etagen exakt auf Wert-10-Feldern des Terrain-Grids.

## GUI-Editor

`stat_editor.py` (Doppelklick auf **„Editor starten.bat"**) — grafischer Editor:

- **Tab „Charaktere":** alle 255 Einheiten durchsuchbar; Filter
  „Nur spielbare" (★ = Typ 1, 119 Einheiten) / „Nur Gegner/NPC"; editierbar:
  Typ, Level, HP, SP, ATK, DEF, SPI, SPD, MOV, Ausrüstung, Fähigkeiten.
  Der Button **„Skills wählen..."** öffnet einen Picker mit ZWEI getrennten
  Tabs: *Benutzbare Skills* (im Kampf einsetzbar: Skill-Granter kind=2 mit
  Anzeige des gewährten Skills, Zanpakuto, Bankai, Shunko, Zenkai) und
  *Passive Fähigkeiten* (Skill-Tree: Statuseffekte, Stat-Passiva). Der erste
  Wert der Fähigkeiten-Liste ist die Zanpakuto-/Skill-Set-ID des Charakters
  (Ability 1–79; referenziert auch den Level-Up-Pool in
  db_ability_selection.inc) und wird vom Picker nie verändert.
  db_ability.inc-Typen: 1=Zanpakuto, 2=gewährt Battle-Skill (Token 5 =
  Skill-ID), 3/5/7=Stat-Passiva, 4=Status-Effekt (Token 5 = Voraussetzung
  in der Upgrade-Kette, z. B. Hold 2 ← Hold 1), 6=Bankai, 8=Shunko,
  9=Zenkai, 10/11=Slots, 12=Route End.
  (Typ-Feld: 1 = spielbar/verbündet, 3–6 = Gegnerklassen, 0 = ungenutzt.
  Ob Typ-Änderung allein einen Charakter im Spiel freischaltet, ist ungetestet —
  Freischaltungen können auch im Spielstand liegen.)
- **Crash-Schutz:** Der Client zeigt und akzeptiert ausschließlich die 195
  Einheiten mit vollständigen Kampfdaten (Stats **und** Battle-Sprite in der
  ROM). Die 60 unfertigen Platzhalter (Story-/Anime-Charaktere ohne
  Kampfdaten, z. B. Sasakibe, Omaeda, Isane) sind komplett ausgeblendet und
  werden beim Einsetzen hart geblockt — sie würden das Spiel crashen.
- **Tab „Skills & Fähigkeiten":** alle 116 Battle-Skills (Kidō usw., in den
  Leveln einsetzbar) aus `db_skill.inc` mit Name + Hilfetext; editierbar:
  SP-Kosten und die 1–2 Effektblöcke (Typ/Power/Wert). Daneben die
  Ability-Referenz (298 benannte Fähigkeiten aus `db_ability_name.bin`
  mit Beschreibung) — deren IDs gehören in die Fähigkeiten-Liste des
  Charaktere-Tabs (dort mit Live-Namensvorschau).
- **Stats & Pressure:** Statreihenfolge lt. Spiel-Tutorial: HP, SP, Attack,
  Defense, **Accuracy (HIT), Evasion (EVA)** und **Spiritual Pressure**
  (Chance auf Zusatzschläge; im Kampf per Befehl aufladbar). Startwert
  vermutlich Spalte 18 in `db_status.inc` (Yamamoto 40, Kenpachi 37);
  das Level-Up-Wachstum aller 7 Stats inkl. Pressure steht als 7×4-Matrix
  pro Charakter in `db_growt.inc` (7. Zeile = Pressure).
- **Porträts:** Charakter-Icons werden live aus der ROM dekodiert
  (`/yamada/NCface/nc_FFFVV.bin`: BIOS-Huffman 0x28 → NARC → NCGR/NCLR,
  lineares 8bpp-Bitmap 128×64, links 64×64 = Gesicht; `tools/faces.py`).
  103 der 255 Einheiten haben ein Porträt — Rest zeigt „(kein Portrait)".
- **Tab „Bleach Tower":** Etage 1–30 wählen, Gegner ändern/hinzufügen/löschen
  (Charakter, Level, Position, Blickrichtung); **Kopieren/Einfügen** dupliziert
  eine gewählte Einheit mit allen Werten auf die aktuelle Etage (z. B. dieselbe
  Entity mehrfach); zusätzlich die 8 **Spieler-Startpositionen** (Deploy-Slots
  aus `db_party_9NN.narc`) pro Etage verschiebbar.
- **Randomizer:** Ziel-Level (z. B. 80/90) und Gegneranzahl (min–max)
  wählen → „Etage randomisieren!" ersetzt alle Gegner der Etage durch
  zufällige Charaktere (Level = Ziel ±5; Stats skalieren mit
  **Faktor (1+Level/100)×1.25**, z. B. Ziel 80 → ×2.25; bei ATK/DEF/HIT/EVA
  wird der Anteil über 1.3× Pool-Durchschnitt nur ×1.1 angehoben —
  verhindert untreffbare 95er-EVA-Gegner; 5 Zufalls-
  Skills + 4 Passiva pro Charakter, Verhalten Original/Aggressiv/Defensiv), jeder
  Charakter max. 1× (max. **25 pro Etage** — in-game bisektiert, 26 =
  Crash; Riesen-Sprites wie Jidanbo/Menos sind vom Randomizer
  ausgeschlossen), nur auf begehbaren Feldern, nie auf/neben
  Spieler-Spawns, Blickrichtung zum Deploy-Zentrum; Slots/AI-Daten
  kommen von den Vanilla-Templates der Etage, darüber hinaus werden
  Extra-Slots angehängt (in-game verifiziert).
- **Tab „Char-Designer":** eigene Spezial-Charaktere bauen — einen der
  111 Pool-Charaktere wählen, **umbenennen** (schreibt `s_name.bin`),
  Stats (HP/SP/ATK/DEF/HIT/EVA/MOV/Level/S-Pressure) und Skills/Fähigkeiten
  setzen, mit „Design speichern" festhalten und mit „In aktuelle Etage
  einsetzen" direkt als aggressiven Gegner platzieren. Änderungen gelten
  global für den Charakter (ARM9). Reihenfolge: designen → speichern →
  einsetzen; **nach dem Randomizer nicht mehr randomisieren** (überschreibt
  die Skills). ATK/DEF/HIT/EVA/MOV sind u8 (max. 255).
- **Skill-Chaos (Button):** gibt ALLEN Gegnern der aktuellen Etage je 1–5
  zufällige Battle-Skills, die ihre KI im Kampf einsetzt — ideal direkt nach
  dem Randomisieren für unberechenbare Kämpfe (nutzt den AI-Skill-Mechanismus).
- **AI-Skills-Editor:** Im Tower-Tab Gegner wählen → „AI-Skills..." →
  die Battle-Skills bearbeiten, die die **Gegner-KI** im Kampf einsetzt
  (aus dpos-Subfile 1). So baust du gezielt Heiler-, Kidō- oder
  Debuff-Gegner. Passive Fähigkeiten des Blocks bleiben erhalten.
- **NONCOM-Schutz:** Charaktere mit Kampf-Attribut 0/4 (Healer/Zivilisten:
  Unohana, Hanataro, Female Spirit, Tatsuki, Rukon-Leute …) crashen, wenn
  sie normal angreifen oder Pressure ausführen (in-game verifiziert an
  Female Spirit). Randomizer und Batches lassen sie automatisch weg;
  manuell einsetzen geht mit Warnung (dann nur Skill-Loadouts geben).
- **Preset-Batches:** Dropdown im Randomizer-Bereich setzt thematische
  Gegner-Gruppen auf einen Klick ein (Captains, Bankai-Chars, Arrancar &
  Espada, Vize-Captains, Hollows, Aizen & Verräter, Ichigo & Freunde,
  Zanpakuto-Wesen, Soul-Reaper-Mobs) — mit Ziel-Level, Verhalten und
  Stat-Scaling wie beim Randomizer. Dazu **Rollen-Batches**: Tanks (4:
  Kenpachi, Komamura, Shinji, Edrad), Healer/Support (4: Orihime, Momo,
  Izuru, Nemu), Carries/DPS (4: Arturo, Aizen, Ikkaku, Hiyori) und
  Balanced Lobby (alle 12).
- **Skillpoints:** JEDE Etage belohnt jetzt mit verteilbaren Punkten
  (1–12: 5, 13–25: 10, 26/27: 20, 28/29/30: 50) — via db_result.inc +
  ARM9-Zwilling.
- **iCloud-Sync (iPhone):** ROM und Battery-Save werden automatisch nach
  `iCloudDrive\Modded ROM files` / `Modded DSV files` gespiegelt — beim
  Editor-Speichern sofort, In-Game-Saves über den Hintergrund-Watcher
  („iCloud-Sync starten.bat", startet auch automatisch mit dem Editor).
- **Gegner-Charakterauswahl = `VERIFIED_POOL_IDS` (111 IDs):** JEDE davon
  wurde in Batch-Tests einzeln in-game verifiziert (spawnt mit exakt dem
  eingestellten Level) — alle Hollows, Espada-Versionen, alle 10 Turm-
  Captains (132–144), Gin/Tosen/Aizen, Enemy-Ichigo/Rukia/Yoruichi,
  Vize-Captains (196–227), Soul-Reaper-Mobs (63–68), Zivilisten und
  Zanpakuto-Wesen. Die Einheiten-Dropdown im Tower-Tab listet den Pool
  zuerst; Roster-verknüpfte Einheiten sind mit **[Roster!]** markiert und
  lösen beim Einsetzen als Gegner eine Warnung aus (sie ziehen Level/Stats
  aus dem SPIELSTAND — in-game bestätigt an Rangiku 47 und Shinji 179;
  Erkennung: db_partner.inc Token 1 = 1). `RANDOMIZER_BLACKLIST`
  (176/177 "Whole", 185 Sky Rift) für in-game kaputte Einheiten —
  bei neuen Funden ergänzen. Ungetestet: namenlose IDs 200–235.
- **Auto-Test:** Nach „Alle Änderungen in ROM speichern" beendet der Editor
  laufende DeSmuME-Instanzen und startet DeSmuME automatisch mit der
  gespeicherten ROM (abschaltbar per Checkbox oben).
- **GOD-MODE Lv90+:** wie Randomizer, aber Level 91–99 und die gespawnten
  Charaktere bekommen übertriebene Stats in db_status (HP ×3, SP/ATK/DEF/
  HIT/EVA ×2, einmal pro Session/Charakter).
- **Map-Wechsel pro Etage:** Map-Dropdown im Tower-Tab. Übernimmt beim
  Wechsel die Terrain-/Spawn-Subfiles (1–3) und die Spieler-Startpositionen
  einer Donor-Etage, die die Map original nutzt. Größere Donor-Maps (z. B.
  27/30/31/35) werden beim Speichern automatisch in freien ROM-Platz
  umgezogen (Relocation) — jede Map ist auf jede Etage legbar. Per
  **„Map benennen..."** lassen sich Maps frei beschriften (gespeichert in
  `map_names.json`, nur im Editor sichtbar). Beim Speichern werden
  `db_btower.inc` UND die ARM9-Binärtabelle (@0xf3b58, u16-Tripel
  {Etage, Map, Party}) gepatcht, da unklar ist, welche Quelle die Engine
  liest. Nach Map-Wechsel Gegner am besten neu randomisieren (alte
  Positionen passen nicht zur neuen Map).
- **Kartenansicht:** Die echte Spielfeld-Grafik der Etage wird live aus der
  ROM gerendert (rot = Gegner, blau = Deploy-Slots, gelb = Auswahl, grüne
  Punkte = begehbare Felder). Klick auf einen Marker wählt die Einheit,
  Klick auf eine freie Zelle versetzt die gewählte Einheit dorthin
  (1 Zelle = 8 px; Einheiten-Koordinaten sind 1-basiert, Pixel/Grid
  0-basiert — Marker von Einheit (x,y) liegt bei Pixel ((x−1)·8, (y−1)·8)).

## Spielfeld-Karten (FMap)

`/yamada/FMap/MAPxxx.bin` = BIOS-Huffman(0x28) → NARC mit
NCGR-Tileset (1024 Tiles, 8bpp), NCLR (16×256 Farben) und NSCR-Tilemap
(Feldgröße variiert pro Map, z. B. 512×384 px; bei Karten > 256 px in
256×256-**Screenblöcken** abgelegt). Decoder: `tools/fmap.py`.
Map-ID (Spalte 2 in `db_btower.inc` / Spalte 4 in `db_fbattle.inc`) →
Dateinummer über eine 40er-Tabelle in ARM9-Overlay 1 @ 0x3ada8
(`MAP_TABLE` in fmap.py, 0-basiert; Etage 1 → ID 34 → MAP291).
Alle 30 Etagen-Karten mit Markern liegen in `dumps/maps/`.

**Achtung Baustelle:** `db_btower` liegt zusätzlich **binär im ARM9**
(0xf3b58, u16-Tripel) — die .inc-Datei ist möglicherweise nur ein
Build-Überrest. Vor Story-/Turm-Struktur-Mods (Map-Wechsel einer Etage)
testen, welche der beiden Quellen das Spiel wirklich liest;
Gegner-/Party-Daten (db_dpos/db_party) werden dagegen sicher aus dem
Dateisystem geladen (Ladepfade in ARM9/Overlay 1 gefunden).
- Lädt und speichert standardmäßig **direkt** die Arbeits-ROM
  `Bleach3P modded.nds` (mit Rückfrage); optional in eine Kopie.
  Charakterdaten kommen beim Laden aus der ARM9-Tabelle (der echten
  Engine-Quelle) und werden beim Speichern dorthin zurückgeschrieben.
  Kompletter Wissensstand & Übergabe: **REPORT.md** (zuerst lesen!).

## Tools (`tools/`)

- `romfs.py` — NitroFS lesen + Dateien in die ROM zurückschreiben
- `formats.py` — BGSM-Text, NARC, `.inc`-Parser/-Serializer
- `characters.py` — erzeugt `dumps/characters.csv`, `names.csv`, `abilities.csv`
- `tower.py` — Turm ansehen & umbauen:
  ```
  python tools/tower.py dump                          # -> dumps/tower_dump.txt + tower_floors.json
  # tower_floors.json editieren (char/level/x/y/dir je Einheit, Einheiten löschen/hinzufügen)
  python tools/tower.py build dumps/tower_floors.json out.nds   # patcht Kopie der ROM
  ```

## Dumps (`dumps/`)

- `characters.csv` — alle 255 Einheiten: Name, LV, HP, SP, ATK, DEF, SPI, SPD, MOV, Ausrüstung, Fähigkeiten. (Spalten `unk*` sind noch nicht sicher identifiziert; die Stat-Zuordnung ATK/DEF/SPI/SPD ist begründete Vermutung.)
- `names.csv` — Charakter-ID ↔ Name (1–144 Story-Charaktere, 145+ Hollows/NPCs)
- `abilities.csv` — 513 Fähigkeiten
- `tower_dump.txt` — alle 30 Turm-Etagen mit Gegnern, Leveln, Positionen
- `tower_floors.json` — dieselben Daten, editierbar für `tower.py build`

## Was sich damit ändern lässt

1. **Turm-Etagen umbauen**: Gegnertyp, Level, Position, Blickrichtung, Anzahl
   (bis 113 Gegner-Slots pro Etage), verwendete Map (`db_btower.inc`, Spalte 2).
2. **Charakterwerte**: HP/Stats/Movement/Start-Fähigkeiten in `db_status.inc`
   (Klartext editieren, per `romfs.py` zurückschreiben), Wachstum in `db_growt.inc`.
3. **Story-/Free-Battles**: gleiche dpos-Struktur (`db_dpos_000`–`264`, `8XX`).
4. **Gegner-Level der Free Battles**: letzte Spalte in `db_fbattle.inc`.

Verifiziert: Round-Trip aller 30 Etagen byte-identisch; Testpatch
(`Bleach3P_test_mod.nds`: Etage 1, Slot 16 = Menos Grande LV50) erfolgreich
geschrieben und wieder ausgelesen.
