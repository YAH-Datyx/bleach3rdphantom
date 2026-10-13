# Status der TO-DO-Punkte (Stand 2026-07-08)

## In Arbeit: SPIELSTAND-EDITOR (Live-Stats der Party editieren)
Ziel: Charaktere-Tab richtig machen - LIVE-Werte aus dem Battery-Save
(.dsv) lesen/aendern statt der ROM-Basiswerte (die fuer Roster-Chars
kaum zaehlen). Save-Struktur bereits kartiert: 64K SRAM + Footer,
3 Slots (0x1000/0x4000/0x7000), Charakter-Records mit 156-B-Stride -
aber die FELD-BEDEUTUNGEN sind noch nicht geknackt (Daten wirken
teils gepackt). NAECHSTER SCHRITT = Kalibrier-Diff (siehe unten),
Werkzeug: `python tools/saveedit.py diff alt.dsv neu.dsv`.

**Kalibrier-Protokoll fuer den User (2 Minuten):**
1. Spiel laden, zu einem Charakter gehen und seine EXAKTEN Werte
   notieren/screenshotten (Level, HP, ATK ...).
2. Im Spiel speichern -> im Save-Manager Profil "kalib1" sichern.
3. Im Spiel bei GENAU EINEM Charakter etwas EINDEUTIGES aendern
   (z. B. Bonuspunkte auf ATK legen oder 1 Kampf-XP holen), wieder
   speichern -> Profil "kalib2" sichern.
4. Mir sagen: welcher Char, was geaendert (vorher/nachher-Werte).
Dann kann ich das Feld-Layout exakt bestimmen und den Editor bauen
(inkl. Checksummen-Analyse - die Diffs zeigen auch die Pruefsumme).

## Geparkt (spaeter)
- **Skill-Icons im Editor:** Recherche abgeschlossen, Asset unklar. In der
  ROM gefunden & dekodierbar (tools/cpk.py, CPK/CRILAYLA geknackt):
  123 Charakter-Kopf-Icons 32x32 (FIcon/tex.cpk, ID = person*10, inkl.
  Bankai-Varianten) und Power/Tech/Speed/NonCom-Badges (C_type000).
  Ein Icon-Set PRO SKILL existiert nicht als eigenes Sheet - wenn der
  User zeigt, wo die Icons in-game auftauchen (Screenshot), gezielt
  weitersuchen. Kopf-Icons koennten sofort in Tower-/Designer-Listen.

## PRIO-Punkte

### 1. Yachiru-Endlos-Angriff — ✅ GELOEST
Ursache gefunden: Ability **375 „Hit & Run"** (kind 5, „Enable movement
after attacking"). Die aggressive AI nutzt das als Endloskette:
Angriff → darf ziehen → greift sofort wieder an, bis jemand stirbt.
Yachiru hatte es per Zufalls-Loadout bekommen (dazu Sure Evade + Hold 4).
- Fix 1: 375 ist aus dem Zufalls-Passiva-Pool des Randomizers raus
  (`AI_ABUSE_PASSIVES` in stat_editor.py). Manuell zuweisbar bleibt es.
- Fix 2: Yachirus aktuelles Loadout in der ROM bereinigt (375 entfernt).
- Merken: Hit & Run auf SPIELER-Chars ist dagegen sehr stark und safe.

### 2. Story-/Kampagnen-Maps spielbar machen — ✅ 10 NEUE MAPS
**Maps 1, 5, 8** (Free-Battle-Donoren) + **Maps 3, 9, 12, 18, 23, 28, 32**
(Story-Kampf-Donoren) sind im Map-Dropdown („STORY, Free Battle NN" bzw.
„STORY, Story-Kampf NNN"). Deploy-Slots werden automatisch auf begehbare
Zellen gesetzt; Spawn-/Slot-Subfiles kommen von der eigenen Etage.
Zuordnung der Story-Kaempfe zu Maps: 226→12 durch ARM9-Tabelle belegt,
9→99 + 18→220 visuell EINDEUTIG (Grid passt exakt auf Strassenkreuzung/
Felsental), 3→1, 23→190, 28→229, 32→264 plausibel — Pruefbilder liegen
in `dumps/story_map_matching/` (gruen=begehbar, rot=Rand).
- Map 0 (Dorf/Hof): kein passender Donor gefunden — einziger Kandidat
  (Kampf 11) lag visuell daneben.
- Maps 3/9/18/23/28/32 sind groesser als das 39x39-Terrain-Grid:
  bespielbar ist der Bereich des Original-Story-Kampfs.
- IN-GAME-TEST NOETIG: alle 10 Maps einmal anspielen (Grafik vs.
  Kollision), besonders die 4 „plausiblen".

### 3. Move-Limit >6/7, Stats >100 — 🎮 BEREIT ZUM TESTEN
Der Editor kann das laengst: MOV bis 255, ATK/DEF/HIT/EVA bis 200/255
(u8-Grenzen im ARM9). Einfach im Char-Designer einem Gegner/Char MOV 10
und z. B. ATK 150 geben und in-game schauen, ob die Engine es respektiert.

### 4b. SKILLPOINT-FARM Etage 28 — ✅ FERTIG & IN-GAME VERIFIZIERT!
1-HP-Familiar oneshotten -> 30 Level-XP + **50 Skillpoints** pro
ueberlebendem Char pro Run (db_result.inc + ARM9-Zwilling @0xF8998
beide gepatcht). Etage 30 bleibt vanilla (Credits-Risiko).
Optional spaeter: Punktewert erhoehen (u16) oder weitere Etagen.

### 4. XP-Punkte (Pregame-Lobby) verschenken — ⚠️ QUELLE GEFUNDEN, TEST GECRASHT
Quelle: **db_result.inc** (Zeile pro Etage: Spalte 2 = Bonuspunkte,
Gruppe 4 = Charakter-Freischaltungen). ABER: Der Testaufbau (Bonus 99 +
1 Familiar auf Etage 30) crashte beim Kill sogar DeSmuME → ALLES
zurueckgerollt (Bonus 50, Etage 30 vanilla, Familiar vanilla).
User baut die Farm selbst (Lv1-Mob, 1 HP im Editor). Falls das AUCH
crasht, liegt es an der Etage-30-Sieg-Sequenz, nicht am Mob.
Der 99er-db_result-Patch ist damit UNGETESTET (nicht widerlegt) -
falls gewuenscht, spaeter isoliert testen (nur 99, sonst vanilla).

## Weitere Punkte

| Punkt | Status |
|---|---|
| Randomizer fuer alle Etagen per 1 Button | ✅ Button „ALLE 30 Etagen randomisieren (Challenge-Run)" — nutzt Ziel-Level/Anzahl/Verhalten/Filter/Challenge |
| Batches ein-/ausschliessen im Randomizer | ✅ Dropdowns „Randomizer nur aus:" / „ohne:" (alle Preset-Batches) |
| Challenges mit Kategorie-Sinn | ✅ Erste Challenge: „Gegner spawnen bei den Teammates" (nah am Deploy). Ideen fuer weitere notiert: Pressure-Drain-Lobby (Skill 59 Seeleschneider senkt S-Pressure), First Strike, Split-Spawns, Dauer-Debuffs — sag Bescheid, welche als naechstes |
| Max. Skilltree-Slots fuer ALLE Chars | ✅ Button „ALLE Chars: Slots auf 9 auffuellen" (Char-Designer, fuellt leere Slots mit Zufalls-Passiva; Wirkung bei SPIELBAREN Chars in-game ungetestet) |
| XP-Rewards der Level analysieren | ⚠️ TEILWEISE — XP-Tabelle weiter unbekannt, ABER die Alternative ist umgesetzt (2026-07-08): **Etage 30 = XP-Farm** (1 Familiar Lv1 direkt am Spawn, oneshotten → Sieg-XP). Die originale Etage 30 (Endkampf) liegt jetzt als Komplettkopie auf **Etage 29** |
| Bankai-State-Spawn | ⛔ ABGESCHLOSSEN/AUFGEGEBEN (2026-07-08) — datenseitig komplett widerlegt (AI-Typen + Pressure-100 + Tail + volle Bar → nie Bankai). ARM9-Code-RE brachte die Mechanik-Kette (Flag [unit+0x10]&0x40000 → Sprite _b), aber Aktivierung nur per DeSmuME-Debugger aufloesbar = vom User abgelehnt. Nicht mit vertretbarem Aufwand machbar, Thema zu. Adressen in REPORT 3b0 |
| Sky Rift / Chars als „Spawner" | 🎮 IN-GAME-TEST — Sky Rift (185) ist Team-5-Spezialobjekt von Etage 28 mit eigener Skript-Logik; auf anderen Etagen crasht es als normaler Gegner. Ob die Spawn-Logik uebertragbar ist: Team-Byte 5 + Etage-28-Testaufbau noetig |
| Guest-Funktion | ❌ OFFEN — unbekannter Mechanismus; Kandidat: dpos-Team-Byte-Werte ausser 1/3/5 durchprobieren |
| Item-Drops on death | ❌ OFFEN — Kandidaten: `/chiba/item/sys_item.narc`, `db_item.inc`, unkartierte dpos-raw-Felder (raw[3]? raw[10]?). Naechster Schritt: Vanilla-Etage mit bekanntem Drop nehmen und raw-Felder vergleichen |
| Entry Conditions (Gegner spawnen nach Kill) | ❌ OFFEN — das sind die Wellen-Records in dpos Subfile 1 (x=y=0-Einheiten). Beispiel des Users (Hollows nach 3x3-Kill) = perfekter Testfall: Original-Etage mit diesem Verhalten diffen |
| Level-/HP-Cap umgehen | ❌ OFFEN (sehr low prio) — Lv-Cap 99 und HP-Anzeige vermutlich ARM9-Code, nicht Daten |
