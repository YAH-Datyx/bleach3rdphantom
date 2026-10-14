# ÜBERGABE — Bleach: The 3rd Phantom (EU) Modding-Projekt

> **Für den nächsten Chat.** Dieses Dokument fasst den kompletten Wissensstand,
> den aktuellen ROM-Zustand und den **einen offenen Bug** zusammen.
> Stand: 2026-10-13.
>
> **Lies zusätzlich `REPORT.md` (829 Zeilen)** — das ist die vollständige
> technische Referenz. Dieses Dokument ist die Zusammenfassung + der aktuelle
> Arbeitsstand + die Warnungen.

---

## 0. WICHTIGSTE WARNUNG VORAB

In der Vorgänger-Session wurde eine **falsche Diagnose** gestellt und als
Fix in die ROM geschrieben. Details in Abschnitt 5. Kurzfassung:

> **Die Behauptung "Tower-Gegner brauchen `unk3=15`, sonst bricht die
> HP-Berechnung" ist WIDERLEGT.** Vanilla benutzt quer durch den Turm
> `unk3` = 0, 10, 13, 15, 17, 18 — die **meisten** Etagen nutzen **10**.
> `unk3` ist KEIN Stat-/HP-Flag. Seine echte Bedeutung ist UNBEKANNT.

Wenn in `REPORT.md` oder im Memory noch steht, unk3=15 sei der HP-Fix:
**das ist falsch und muss korrigiert werden.**

---

## 1. Setup & Pfade

| Was | Pfad |
|---|---|
| Projektordner | `C:\Users\danie\OneDrive - Technische Hochschule Rosenheim\Desktop\Bleach3P_RE\` |
| **Arbeits-ROM (DIESE editieren)** | `Bleach3P modded.nds` (134.217.728 B) |
| **Vanilla-Referenz** (nie ändern!) | `Bleach3P_test_mod.nds` |
| Emulator | `desmume-0.9.13-win64\` (im Projektordner) |
| Spielstand | `desmume-0.9.13-win64\Battery\Bleach3P modded.dsv` |
| iCloud ROM (fürs iPhone) | `C:\Users\danie\iCloudDrive\Modded ROM files\` |
| iCloud DSV | `C:\Users\danie\iCloudDrive\Modded DSV files\` |

**Starten:** `Editor starten.bat` (lädt die ROM automatisch).
**Selbsttest nach JEDER Code-Änderung:** `python stat_editor.py --selftest`

**Python-Zugriff auf die ROM:**

```python
import sys; sys.path.insert(0,'tools')
from romfs import RomFS
from tower import load_names, floor_units, party_slots, pack_units, narc_subfiles
fs = RomFS('Bleach3P modded.nds')
units = floor_units(fs, 15)          # Einheiten einer Turm-Etage
fs.write('/yamada/DataBase/db_dpos_915.narc', data)
```

Unter Windows immer `PYTHONIOENCODING=utf-8` setzen (sonst crasht die
Konsolenausgabe bei Sonderzeichen).

---

## 2. Dokumenten-Landkarte

| Datei | Inhalt |
|---|---|
| **REPORT.md** | Vollständige technische Referenz (Formate, Offsets, Chronik) |
| **README.md** | Toolkit-Überblick, Editor-Funktionen |
| **HANDOVER.md** | dieses Dokument |
| CUSTOM_CAMPAIGN.md | Lore + Aufbau der 5-Kapitel-Kampagne (Etagen 11-15) |
| EDITOR-VISUALS.md | Visuelle Beschreibung des Editors (für Design-AI) |
| HANDY-SYNC.md / HANDY-EDITOR.md | iPhone-Workflow, Mobil-Editor |
| TO DO NOTIZEN UND IDEEN/ | Backlog des Users (docx + STATUS.md) |

---

## 3. KERN-WISSEN (alles in-game verifiziert)

### 3.1 Die goldene Regel

> **`.inc`-Dateien sind BUILD-ARTEFAKTE.** Die Engine liest die kompilierten
> Tabellen im **ARM9**. Immer BEIDE patchen — der ARM9 ist maßgeblich.

### 3.2 ARM9-Tabellen (ROM-Offsets)

| Tabelle | Offset | Record |
|---|---|---|
| **Stat-Tabelle** | `0x101C52 + (unit-15)*70` | 70 B |
| **Growth-Tabelle** | `0x105E84 + unit*76` | 76 B |
| **Turm-Belohnungen** (db_result-Zwilling) | `0xF8998 + (floor-1)*68` | 68 B |
| **Btower** (Etage→Map/Difficulty) | `0xF7B58 + (floor-1)*6` | 6 B: `{floor, difficulty, dposRef}` |

**GEKLÄRT (2026-10-13):** `REPORT.md` nennt `0xf3b58`, wir lesen bei
`0xF7B58` — **beides ist korrekt**, nur zwei Bezugssysteme:
`0xf3b58` ist der Offset *innerhalb von arm9.bin*, `0xF7B58` der Offset
*in der ROM-Datei*. Der ARM9 liegt in der ROM bei `0x4000`:
`0xf3b58 + 0x4000 = 0xF7B58`.
**Merkregel:** `ROM-Offset = arm9.bin-Offset + 0x4000 = RAM − 0x02000000 + 0x4000`.
Gegengeprüft gegen das GitHub-Repo (US-ROM) — identische Werte. Details in
`KNOWLEDGE_MERGE.md`.

**Stat-Record (70 B), relevante Felder:**

```
+4  u16 person (-> Sprite bat_main_nc{person:03d}.bin)
+6  u16 unit   (Pruef-Key: muss == unit sein)
+8  typ   +9 unk3   +10 face   +11 lv
+12 u16 HP   +14 u16 SP
+16 ATK  +17 DEF  +18 HIT  +19 EVA  +20 MOV   <- alles u8, max 255!
+21 attackType (0/4 = NONCOM -> Crash-Gefahr)
+26 S-Pressure
+28 u16[10] Equip
+50 u16[10] Faehigkeiten   <- Slot 0 = Zanpakuto-Set-ID, NICHT aendern!
```

**Growth-Record (76 B):**

```
+0  u16 unit-Echo (Pruef-Key)
+2  u16 HP-Growth      +4 u16 SP-Growth
+12..+67  28x u16 Level-Up-Wahrscheinlichkeiten (0 oder 100)
+68..+75  TAIL-BYTES  <- entscheidend, s. u.
```

### 3.3 Wie Gegner-Stats zustande kommen (WICHTIGSTES KONZEPT)

| Stat | Quelle bei Gegnern |
|---|---|
| **ATK / HIT / EVA** | **roh aus der Stat-Tabelle** (Edits wirken direkt) |
| **HP / DEF** | **NICHT** aus der Tabelle — über die **Wachstumsformel berechnet** |

Gesteuert wird das von den **Growth-Tail-Bytes** (`+68..+75`):

- **alle null** (= alle Gegner-Units) → Turm **berechnet** HP/DEF, Tabelle ignoriert
- **nonzero** (z. B. `01 01 0a 0a 0a 0a 0a 00`) → Turm liest HP/DEF **aus der Tabelle**

**Tail-Trick nur bei Lv-1-Einheiten sicher!** Bei hochstufigen Gegnern
behandelt die Engine den Tabellenwert als Lv-1-Basis und wächst ihn hoch →
absurde Stats.
Beweis: Familiar mit Tabellen-HP 1 + Null-Tails zeigte in-game **3480 HP**.

### 3.4 dpos — die Kampf-Daten (`db_dpos_9NN.narc`, NN = Etage)

4 Subfiles:

| # | Inhalt |
|---|---|
| **0** | 128 Einheiten-Records à **54 Bytes** |
| **1** | **AI-Skill-Skripte pro Einheit** (72-B-Header + 72-B-Block je Record in Slot-Reihenfolge) |
| **2** | **39x39 Terrain-Grid**: `10`=begehbar, `0`=Rand, `255`=void |
| 3 | unbekannt (1521 oder 2067 B) |

**Record (54 B):**

```
u8 slot(1-basiert) | u8 TEAM | u16 char | u16 level | u16 unk3 |
u16 x | u16 y | u16 dir | u16 unk7 | u16 raw[18]
```

- **TEAM:** `3`=Gegner, `1`=Spieler, `5`=Objekt (z. B. Sky Rift)
- **unk3:** `u8 ai_mode` bei `+0x06`, dahinter ein Flags-Byte bei `+0x07`
  (in Vanilla immer 0, deshalb ist die u16-Lesart folgenlos). Vermutlich
  `10`=aktiv/boss, `15`=passiv/patrol — **kein Stat-Flag** (bewiesen).
- **dir:** `0`=Ost(+x), `1`=Nord(-y), `2`=West(-x), `3`=Süd(+y)
- **`raw[0]` = WELLE** (`s16` bei `+0x10`): **nur Welle 0 spawnt beim Betreten**
  der Etage, `1/2/3` sind Nachschub, `-3` (=65533) Sonderfälle (Objekte,
  `x=y=0`). Aus Ghidra (`FUN_02182068`) und gegen alle 499 Vanilla-Records
  geprüft: trennscharf, keine Ausnahme. Merkregel: `raw[n]` liegt bei `+0x10+2n`.
- **raw[1]** = AI-Typ, **raw[2]** = Aggression 0-100 (Vanilla: `3/100` = jagt
  aktiv, `0/0` = wartet defensiv)
- Sonder-Records (`raw[0] = -3`): `x=y=0`, `unk7=10`

### 3.5 Koordinaten (häufige Fehlerquelle)

> Einheiten-Koordinaten sind **1-basiert**, Terrain-Grid und Pixel **0-basiert**.
> Einheit `(x,y)` steht auf Grid-Zelle `(x-1, y-1)`. (An 739/739 Einheiten verifiziert.)

### 3.6 Harte Limits

- **25 Gegner pro Etage** = OK, **26 = CRASH** (in-game bisektiert). Die Ursache
  ist **nicht** das Sprite-Limit, sondern **32 Aktor-Plätze, die die Party
  zuerst belegt** (Ghidra, `FUN_02182068`): `25 + 6 Deploy = 31 ≤ 32`.
  Gezählt werden **Einheiten, nicht Sprites** — Dubletten kosten auch Plätze.
  Ungetestet, aber vorhergesagt: weniger Deploy-Slots → mehr Gegner möglich.
- **Nur die ersten 64 dpos-Slots** werden überhaupt gelesen (unsere Extra-Slots
  gehen bis 40, liegen also sicher darunter)
- **Riesen** (BIG_UNITS: Grand Savage 148-150, Menos 163-165, Huge Hollow
  166-168, Jidanbo 237, Giant Entity 252) fressen 4 Felder → aus Randomizer raus
- **NONCOM** (attackType 0/4: Unohana, Hanataro, Female Spirit …) **crashen
  beim Angreifen/Pressure** → aus Randomizer raus
- Stat-Felder ATK/DEF/HIT/EVA sind **u8** → max 255

### 3.7 Charakter-Pool

- `VERIFIED_POOL_IDS` (111 IDs) = explizite, in-game getestete Whitelist
- minus Blacklist (176/177 "Whole", 185 Sky Rift, 151 Familiar) = **110**
- minus 11 Riesen minus 10 NONCOM = **89 effektiv würfelbar**
- **Roster-Falle:** Chars mit `db_partner.inc`-Flag=1 ziehen ihre Stats aus dem
  **Spielstand** → spawnen unterlevelt. Nur Flag-0-Chars verwenden.

---

## 4. AKTUELLER ROM-ZUSTAND

### 4.1 Turm-Etagen

| Etage | Inhalt |
|---|---|
| 1 | 25 Gegner Lv45 — der verifizierte 25er-Limit-Test, läuft sauber |
| 11-15 | **Custom-Kampagne** (s. 4.2) — **HP-BUG, s. Abschnitt 5** |
| 28 | XP-/Skillpoint-Farm (1 Familiar Lv1, 50 Bonuspunkte) |
| 29 | Komplette Kopie der Vanilla-Etage 30 (echter Endkampf) |
| 30 | Vanilla (XP-Farm-Versuch wurde zurückgerollt — crashte) |

### 4.2 Kampagne Etagen 11-15 (exakter Ist-Zustand)

Alle 5 Etagen: **50 Bonus-Skillpoints**, Gegner **gruppiert** (Durchmesser 4-6
Felder, 8-12 Felder vor der Deploy-Zone), alle **blicken zum Deploy-Zentrum**,
keine Overlaps, alle auf begehbarem Terrain, `unk3=15` (fragwürdig, s. o.).

```
Etage 11 (Lv15, Deploy 20,26): Screamer145 Familiar151 HellMantis154
                                FrogHead157 WideBone160 MadEater131
Etage 12 (Lv30, Deploy 30,22): Izuru196 Momo206 Renji207 Hisagi208
                                Yachiru216 Ikkaku217 Yumichika218
                                Rangiku209 Nemu227
Etage 13 (Lv45, Deploy 25,32): Screamer145 HellMantis154 WideBone160
                                MadEater131 + Kenpachi141 Byakuya136
                                Hitsugaya140 (hinten)
Etage 14 (Lv60, Deploy 31,25): Shawlong119 Edrad121 Ilfort123 D-Roy125
                                Nakeem127 EvilEater186/187 Nemu227
                                + Ulquiorra113 Grimmjow115 Yammy117 (hinten)
Etage 15 (Lv90, Deploy 18,27): Kenpachi141 Byakuya136 Hitsugaya140
                                Ulquiorra113 Grimmjow115
                                + BOSS Arturo129 Lv95 (hinten)
```

**Etage 15 ist ein laufendes Isolations-Experiment:** alle 6 dpos-Records sind
byte-genaue Klone der **Vanilla-Etage-30-Records** (dort laufen dieselben Chars
auf Lv83-90 nachweislich korrekt). Nur Position/Blick/Level sind angepasst.
Byakuya/Hitsugaya nutzen Yamamoto-/Soi-Fon-Templates. **Zusätzlich** wurde
Ulquiorras Stat-Record komplett auf Vanilla zurückgesetzt (Kontrollprobe) —
darum hat er aktuell niedrige ATK (17). Das ist **Absicht**, kein Bug.

### 4.3 Backups

| Datei | Zeitpunkt / Zustand |
|---|---|
| `…bak-unk3fix.nds` | 25.07. — vor dem (falschen) unk3-Fix |
| `…bak-campaignfinal.nds` | 27.07. 15:53 — vor Stat-Boosts/Skillpoints |
| `…bak-regroup.nds` | 27.07. 16:02 — vor der Neugruppierung |
| `…bak-f15clone.nds` | 27.07. 16:11 — vor dem Etage-15-Experiment |

---

## 5. DER OFFENE BUG — kaputte Gegner-HP (53 / 11)

### 5.1 Symptom

Auf den Kampagnen-Etagen spawnen Gegner mit absurd niedrigen HP.
**53 HP ist der häufigste Wert, auch 11 HP.** User-Report zu Etage 15:
Kenpachi 53 HP, Ulquiorra 11 HP. Betroffen sind hochstufige Chars (Lv60-95),
die eigentlich tausende HP haben müssten.

### 5.2 Was AUSGESCHLOSSEN wurde (nicht nochmal prüfen!)

| Verdacht | Befund |
|---|---|
| Growth-Daten korrupt | NEIN — Growth-Tabelle **byte-identisch** mit Vanilla (außer Familiar-Tails) |
| Level außerhalb der Range | NEIN — Vanilla-Turm geht selbst bis **Lv90** (Etage 30) |
| Positionen/Terrain kaputt | NEIN — keine Overlaps, alles begehbar |
| Btower-Difficulty verstellt | NEIN — identisch mit Vanilla |
| NARC-Struktur beschädigt | NEIN — Größen + Subfiles identisch mit Vanilla |
| HP-Low-Byte-Überlauf (53 = HP & 0xFF) | NEIN — passt zu keinem Char |
| **`unk3` = 10 statt 15** | **WIDERLEGT** — Vanilla nutzt 0/10/13/15/17/18, meist **10** |

### 5.3 STÄRKSTER VERDACHT: Fähigkeiten 370 & 401 — Fix ist eingebaut, TEST OFFEN

> **Stand 2026-10-14: Der Fix ist im Editor, die Reparatur auch.
> Was fehlt, ist dein DeSmuME-Test.** Ablauf unten in 5.3.1.

**Genau 59 Vanilla-Einheiten tragen 370 und 401** (beide, immer zusammen —
aus `dumps/characters.csv` ausgezählt). Beide sind `kind=4` in
`db_ability.inc` mit dem Wert `999` — sieht nach einem **Cap/Limit oder
Stat-Grundstock** aus.

**Wichtige Präzisierung:** Es ist *nicht* „jeder Kampfchar". Es sind die
**benannten** Einheiten — Captains, Espada, Vize-Captains. **Nicht** dabei:
Hollows (Screamer, Mad Eater, Hell Mantis, Wide Bone, Frog Head, Familiar,
Menos …), die Soul-Reaper-Mobs 63-68, Zivilisten und Zanpakuto-Wesen.
Auch Yamamoto (1) und Ichigo (94) haben sie nicht.

> **Das passt exakt zum Schadensbild:** Alle gemeldeten Kaputt-Fälle
> (Kenpachi 141, Ulquiorra 113 — Etage 15, Lv90) sind Einheiten **mit**
> 370/401, denen der Randomizer sie weggewürfelt hat. Die Hollow-Etage 11
> besteht ausschließlich aus Einheiten, die sie **nie** hatten — und von dort
> gibt es keine HP-Meldung. Die Korrelation hält also auch nach dem
> genaueren Auszählen.

**Die Skill-Randomisierung des Editors überschreibt die Ability-Slots 1-9 und
löscht damit 370 und 401.** Beispiel Kenpachi:

```
vanilla: [75, 242, 370, 401, 0, 0, 0, 0, 0, 0]
modded : [75, 163, 165, 140, 120, 137, 302, 360, 364, 368]   <- 370/401 WEG
```

Der Zanpakuto-Set-ID in Slot 0 bleibt korrekt erhalten — nur 370/401 fallen raus.

**Korrelation:** genau die Chars mit zerstörten Abilities zeigen 53/11 HP.
Ulquiorra ist aktuell der einzige mit intakten `[36, 377, 370, 401, …]` —
weil er als Kontrollprobe zurückgesetzt wurde.

#### 5.3.1 Was eingebaut ist (2026-10-14)

| Was | Wo |
|---|---|
| Referenz: welche 59 Einheiten hatten 370/401 | `dumps/vanilla_ref.json` → `essential_abil`, erzeugt von `tools/gen_essential_abil.py` |
| Konstanten `ESSENTIAL_ABILITIES` / `ESSENTIAL_ABIL` | `stat_editor.py` (bei `AI_ABUSE_PASSIVES`) |
| Würfeln löscht sie nicht mehr | neues `_abil_loadout()`, genutzt von `_boost_stats` |
| Sie werden auch nicht mehr an Chars **verteilt**, die sie nie hatten | aus beiden `passives`-Pools ausgeschlossen |
| Reparatur bereits beschädigter Chars | Button **„370/401 reparieren"** (grün) im Tower-Tab, Methode `_repair_essential_abil` |
| Regressionstest ohne ROM | `python tools/test_essential_abil.py` |

Das Loadout hat jetzt 7 Zufalls-Skills (4 aktiv / 3 passiv) + 370 + 401 auf
den Slots 8 und 9 — **hinten**, genau wie in Vanilla (Kenpachi: `242 370 401`).
Das ist bewusst so: falls die beiden als Terminator/Cap wirken, muss alles
Echte **davor** stehen. Chars ohne Anspruch behalten 9 Zufallswerte.
Die Reparatur ist idempotent und lässt Slot 0 in Ruhe.

> **DEIN NÄCHSTER TEST:**
> 1. Editor starten, Tower-Tab, Button **„370/401 reparieren"** → er sagt dir,
>    wie viele Chars betroffen waren.
> 2. Speichern, Etage 15 in DeSmuME spielen (über „Continue", **nicht**
>    über einen Savestate!).
> 3. **HP von Kenpachi (141) und Ulquiorra (113) melden** — ATK/ACC/EVA mit
>    dazu, dann füllt sich auch die Tabelle in 5.4.
>
> - **HP normal** → Ursache gefunden, Bug zu. Ulquiorra bleibt schwach (ATK 17),
>   das ist die Kontrollprobe und Absicht.
> - **HP weiter 53** → nächster Verdächtiger ist das **AI-Subfile 1**
>   (bei Etage 15 wich Block 1 von Vanilla ab: mod `ids=[]` vs. vanilla
>   `ids=[5,26,17,13,107,372,344,371]`). Danach die HP-Formel am **Code**
>   aufrollen statt am Verhalten: der Ghidra-Zweig im GitHub-Repo hat die
>   Toolchain dafür (`tools/re/ghidra/`, headless), und die Frage „wer liest
>   die Stat-Tabelle `0x020FD882`?" ist dort schon als Ziel notiert.

### 5.4 Zweiter Hinweis: Stat-Tabellen-Level

Die Stat-Tabelle hat ein eigenes `lv`-Feld (`+11`), das bei den Kampagnen-Chars
stark streut: Kenpachi 20, Byakuya 23, Hitsugaya 18, **Ulquiorra 1,
Grimmjow 1**, Arturo 15. Falls die Wachstumsformel von diesem Basis-Level
ausgeht, könnten `lv=1`-Chars auf Lv90 etwas anderes berechnen als `lv=20`-Chars.
Ungeprüft, aber billig zu testen.

---

## 6. Randomizer-Fairness (analysiert, NICHT gefixt)

Der User bemängelte ungleiche Chancen. **Die Ziehung selbst ist korrekt
uniform** (`random.sample`; 6000 simulierte Etagen: 14,4 %–17,2 %, reines
Rauschen). Zwei echte systematische Effekte:

1. **21 Units sind dauerhaft gesperrt** (11 Riesen + 10 NONCOM) → werden nie
   gezogen. So gewollt, erklärt aber "manche seh ich nie".
2. **Sprite-Mehrfachbelegung:** mehrere Unit-IDs teilen sich einen Sprite.
   Der Randomizer würfelt über Unit-IDs, der Spieler erkennt aber Figuren:

   | Figur | Unit-IDs | Chance/Etage |
   |---|---|---|
   | M. Soul Reaper | 63, 64, 65 | **47 %** |
   | F. Soul Reaper | 66, 67, 68 | **47 %** |
   | Myo-oh / Ashisogijizo / Kyoraku / Yoruichi / Ichigo | je 2 | 31 % |
   | die anderen 73 Figuren | je 1 | **16 %** |

**Empfohlener Fix (vom User noch nicht beauftragt):** Ziehung auf Sprite-Ebene —
erst eine der 80 Figuren uniform würfeln, dann eine ihrer Unit-IDs. Zwei Zeilen
in `_randomize_floor`.

---

## 7. FALLEN — nicht wiederholen

1. **`unk3=15` ist kein HP-Fix** (s. o.). Die Kampagnen-Etagen stehen auf 15.
   Vanilla ist **f11=13, f12=10, f13=10 — f14/f15 sind mit 15 schon korrekt**.
   Betroffen ist also nur 11-13, und für das Etage-15-Experiment ist `unk3`
   **kein Störfaktor**. Zurücksetzen: `python tools/fix_unk3.py` (Trockenlauf),
   `--write` zum Anwenden, `--mode aktiv` für die „10 = aggressiv"-Wette.
2. **Bankai für Gegner: unmöglich per Daten.** Volle Testmatrix (AI-Skript-IDs,
   Pressure 100, Tail-Bytes, volle Leiste) — Gegner nutzen NIE Bankai. Trigger
   liegt im Battle-CODE. **Der User lehnt Execute-Breakpoints ab** ("hat nie
   funktioniert + unendlich Zeit gefressen"). **GESCHLOSSEN, nicht neu aufrollen.**
3. **Passiv 375 "Hit & Run"** lässt die AI endlos Angriff→Zug→Angriff ketten
   (in-game bei Yachiru). Steht in `AI_ABUSE_PASSIVES`, aus Zufalls-Loadouts raus.
4. **Savegame (.dsv) hat eine Prüfsumme** — Byte-Edit → "data is corrupt".
   Save-Editing ist ungelöst.
5. **Etage 30 nicht umbauen:** XP-Farm-Versuch crashte Spiel UND DeSmuME beim
   Kill (vermutlich Sieg-/Credits-Sequenz). Farm liegt jetzt auf Etage 28.
6. **`.inc`-Dateien nie global umformatieren** (Kenpachi-Klon-Crash). Wenn eine
   `.inc` zu groß wird: Write überspringen, ARM9 ist maßgeblich.
7. **Savestates (.ds0-9) nicht zum Verifizieren benutzen** — die backen den alten
   ROM-RAM ein. Immer über "Continue" ins Spiel.
8. **Debuff-Wissen nur aus dem Spiel ziehen** (`db_tutorial_msg.bin [14]`), nicht
   aus Internet-Wissen — das war beim ersten Versuch größtenteils falsch.
   Korrekt: Burned = ATK/DEF-Drop, Frozen = ACC/EVA-Drop.

---

## 8. Nächste Schritte (Priorität)

1. **HP-Bug: Test aus 5.3.1 durchführen.** Fix und Reparatur-Button sind
   eingebaut, es fehlt nur der DeSmuME-Lauf auf Etage 15.
2. **`unk3` zurücksetzen** auf den Etagen 11-13 (14/15 sind korrekt):
   `python tools/fix_unk3.py --write`. Nebenbei der Test, ob 10 die Gegner
   aggressiver macht (`--mode aktiv`).
3. **Randomizer-Fairness** auf Sprite-Ebene umstellen (Abschnitt 6) —
   noch nicht beauftragt. Der zweite Grund für „manche sehe ich nie" ist
   dagegen **gefixt**: der Randomizer klonte auf den Etagen 5/6/9/23/24
   Nachschub-Slots mit `raw[0] != 0`, die beim Betreten gar nicht spawnen
   (s. `KNOWLEDGE_MERGE.md`). Jetzt wird `raw[0] = 0` erzwungen.
3b. **Gegner-Limit nachmessen:** Laut Decompiler sind es 32 Aktor-Plätze
   minus Deploy-Slots, keine 25 Sprites. Test: 30 Gegner mit nur 10
   verschiedenen Charakteren. Läuft das, kann `MAX_UNIQUE_SPRITES` hoch.
4. Editor-Redesign — `EDITOR-VISUALS.md` liegt bereit für eine Design-AI.
   Constraint: tkinter/ttk, keine runden Ecken/Schatten, nur System-Fonts.
5. Offen im Backlog: XP-Belohnungen, Item-Drops, Wave-/Entry-Conditions,
   Guest-Funktion, Sky-Rift-Spawner, Level-/HP-Cap.

---

## 9. User-Profil (für die Zusammenarbeit)

- Kommuniziert **informell auf Deutsch** — bitte ebenso antworten.
- Testet **selbst und schnell** in DeSmuME und meldet Ergebnisse zurück.
  → Änderungen immer so bauen, dass sie **einzeln testbar** sind (bisektieren!).
- Will **starke, aggressive Gegner**, aber keine unfairen Ausweichwerte
  (EVA > ~70 macht Gegner unantastbar — "Yoruichi-Problem").
- Spielt auch auf dem **iPhone** (DeSmuME) — ROM/DSV laufen über iCloud.
- Mag **keine Zeitverschwendung** an Sackgassen (s. Bankai). Lieber früh sagen,
  wenn etwas nicht geht, als lange erfolglos probieren.
