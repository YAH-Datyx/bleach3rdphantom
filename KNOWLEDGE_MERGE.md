# Wissens-Abgleich: lokales Toolkit ↔ GitHub-Repo

> Abgleich der **zwei parallelen Wissensbasen** zu Bleach: The 3rd Phantom.
> Erstellt 2026-10-13 von Session "BLEACH 3P".

## Die zwei Quellen

| | Lokales Toolkit | GitHub-Repo |
|---|---|---|
| Ort | `Desktop\Bleach3P_RE\` | `github.com/YAH-Datyx/bleach3rdphantom` |
| ROM-Version | **EU** (4717, En/Fr) | **US** (4191, Venom) |
| Stand | Juli 2026 | Mai 2026 |
| Default-Branch | `main` (neu) | `claude/nice-volta-9kI3i` |
| Umfang | REPORT.md 829 Z. + Editor + dumps/ | docs/ 696 Z. + tools/scripts/ |
| Ansatz | NitroFS-Toolkit, GUI-Editor | arm9.bin-Patching, CLI-Skripte |

Zweiter Branch im Repo: `claude/ecstatic-dirac-153vh5` — **ausgewertet 2026-10-14**,
siehe Abschnitt „Ghidra-Zweig". Der Branch enthaelt eine **Decompiler-Analyse**
(Ghidra 11.4.2 headless, arm9 + Overlay 1) und ist damit die erste Quelle im
Projekt, die nicht auf Beobachtung, sondern auf gelesenem Code beruht. Dadurch
sind die Widerspruechen A–D unten entscheidbar geworden.

---

## ✅ AUFGELÖSTE WIDERSPRÜCHE

### 1. Tower-Tabelle: `0xf3b58` vs. `0xF7B58` — beide richtig!

Das war in `HANDOVER.md` als offene Frage markiert. **Gelöst:**

```
GitHub : arm9.bin-Offset 0xf3b58   (RAM 0x020F3B58)
Lokal  : ROM-Datei-Offset 0xF7B58
ARM9 liegt in der ROM bei 0x4000  ->  0xf3b58 + 0x4000 = 0xF7B58  ✓
```

**Es ist dieselbe Tabelle, nur zwei Bezugssysteme.** Gegengeprüft an unserer
EU-ROM — die Werte stimmen exakt mit den im Repo dokumentierten überein:

| Floor | gelesen (EU) | Repo dokumentiert (US) |
|---|---|---|
| 1 | `{1, 34, 1}` | `{1, 34, 1}` |
| 5 | `{5, 4, 5}` | `{5, 4, 5}` |
| 14 | `{14, 15, 14}` | `{14, 15, 14}` |
| 30 | `{30, 31, 30}` | `{30, 31, 30}` |

**Merkregel für künftige Offsets:** `ROM-Offset = arm9.bin-Offset + 0x4000`
(bzw. `= RAM-Adresse − 0x02000000 + 0x4000`).

### 2. Stat-Tabelle: ebenfalls dieselbe

```
GitHub : arm9.bin 0xfd882 + (char_id-1)*70   ->  ROM 0x101882
Lokal  : ROM 0x101C52 + (unit-15)*70         ->  unit 1 bei ROM 0x10187E
Differenz: exakt 4 Bytes
```

Beide beschreiben dieselbe Tabelle mit identischem 70-Byte-Stride. Die 4 Bytes
Versatz sind unser `+4 person`-Feld — das Repo lässt den Record erst dort
beginnen, wo wir `+4` zählen.

### 3. US- und EU-ROM haben (hier) identische Offsets

Überraschend, aber verifiziert: Tower- und Stat-Tabelle liegen in beiden
Regionen an derselben Stelle. **Die US-Erkenntnisse des Repos sind also
weitgehend übertragbar** — trotzdem jeden neuen Offset einzeln gegenprüfen.

---

## Ghidra-Zweig `claude/ecstatic-dirac-153vh5` (ausgewertet 2026-10-14)

Neue Dateien dort: `docs/spawn-logic.md`, `docs/gamedata-format.md`,
`docs/re-methods.md`, ein JSON-Exporter (`tools/scripts/gamedata.py`) und eine
Ghidra-Headless-Toolchain (`tools/re/ghidra/`). Der decompilierte Code selbst
ist nicht committet, nur die Beschreibung.

**Kern: die Spawn-Funktion ist gelesen.** `FUN_02189A58` (Floor-Zustands-
maschine, Overlay 1) laedt in Schritt 0 die Map aus dem Tower-Eintrag, in
Schritt 3 `db_dpos_%03d.narc` mit `900 + floor`, in Schritt 4 spawnt
`FUN_02182068(ctx, team, side, wave, posCheck)`. Dabei:

1. Zuerst kommen die bis zu **8 Party-Mitglieder** in die Aktor-Tabelle.
2. Dann laeuft eine Schleife ueber die dpos-Records, **Abbruch nach Index 63**.
3. Ein Record spawnt nur, wenn `char_id != 0`, das Feld `wave` **exakt** dem
   uebergebenen Wellen-Parameter entspricht (Tower-Start uebergibt **0**), und
   die Filter auf Byte +1 und Feld +0x0E passen.
4. Jeder Spawn braucht einen der **32 Aktor-Plaetze** (je 0x13C Bytes).

**Gegengeprueft gegen unseren Vanilla-Dump** (`dumps/tower_floors.json`,
499 Records / 30 Etagen) — das Skript dazu ist `tools/test_essential_abil.py`
bzw. die Auswertung unten. Alle drei Pruefungen fielen eindeutig aus.

---

## ✅ WIDERSPRÜCHE A–D — jetzt entschieden

### A. Feld `0x02` der Tower-Tabelle = **`map_id`** ✔ GEKLÄRT

Der Decompiler zeigt es direkt: Schritt 0 der Floor-Zustandsmaschine ruft
`FUN_0217E5D4(ctx, tower.map_id)` — das Feld geht als Argument in den
Map-Lader. Zusammen mit unserem In-Game-Beweis (Etage 1 → Hafen-Map durch
Patchen genau dieses Feldes) ist die Sache erledigt.

> **„difficulty" ist tot.** Die Deutung war eine frühe Vermutung und ist nie
> bewiesen worden. In `REPORT.md`/Memory überall ersetzen.

Das dritte Feld des 6-Byte-Records ist nicht `dposRef`, sondern was der
Ghidra-Zweig `floor_echo` nennt: eine eigene ID, die ab einem Fortschrittswert
> 89 in ein anderes Objekt übernommen wird. In Vanilla ist sie durchgehend
gleich der Etagennummer. Bedeutung weiter offen (BGM/Szenario?).

### B. Gegner-Obergrenze = **32 Aktor-Plätze minus Party** ✔ GEKLÄRT

Keine der beiden Vorversionen war ganz richtig:

- „Hardcoded pro Floor-Index" (GitHub) — **falsch**, es gibt keinen solchen Code.
- „25 unique **Sprites**" (lokal) — **die Zahl stimmt, die Begründung nicht.**

Es gibt genau **32 Aktor-Plätze**, und die Party belegt sie zuerst. Unser
bisektierter Wert passt exakt: `25 Gegner + 6 Deploy-Slots = 31 ≤ 32`, und
`26 + 6 = 32`+ sprengt es. Das Limit zählt **Einheiten, nicht Sprites** —
Dubletten desselben Charakters kosten also auch je einen Platz.

> **Testbare Vorhersage:** 30 Gegner, aber nur 10 verschiedene Charaktere.
> Sprite-Theorie sagt „läuft", Aktor-Theorie sagt „crasht/fehlt".
> Umgekehrt: mit nur 3 Deploy-Slots müssten **29** Gegner laufen.
> `MAX_UNIQUE_SPRITES = 25` im Editor ist also zu konservativ *und* falsch
> benannt — bis zum Test bleibt es aber sicherheitshalber stehen.

Zusätzlich hart: **nur die ersten 64 dpos-Slots** werden überhaupt gelesen.
Unsere Extra-Slots bis 40 liegen sicher darunter. ✔

### C. `unk3` = **`ai_mode` bei +0x06 (u8!)** ✔ Layout geklärt, Bedeutung plausibel

Der Decompiler liest das Feld als **`u8` bei +0x06** und übergibt es als
Festkomma (`<<12`) an `FUN_020A2688`; bei +0x07 folgt ein **eigenes
Flags-Byte** (1 → Aktor-Flag 0x40000, 2 → 0x1000). Unser Toolkit liest an
der Stelle ein `u16`.

**Gegenprobe (499 Vanilla-Records): kein einziger Record hat `unk3 >= 256`.**
Das Flags-Byte bei +0x07 ist in Vanilla also durchgehend 0 — unsere
u16-Lesart liefert dadurch denselben Wert, und alle bisherigen
unk3-Schreibzugriffe haben nichts kaputt gemacht. **Entwarnung.** Dass es ein
Verhaltensfeld ist (10 = aktiv/boss, 15 = passiv/patrol), bleibt plausibel,
ist aber weiter nicht in-game bestätigt.

Vanilla-Verteilung (aus unserem Dump, 499 Records):

| unk3 | Vorkommen |
|---|---|
| 10 | 281× |
| 15 | 80× |
| 18 | 76× |
| 0 | 42× |
| 13 | 19× |
| 17 | 1× |

> **Praktische Folge, jetzt genauer:** Die Kampagnen-Etagen stehen pauschal
> auf 15. Vanilla ist **Etage 11 = 13**, **Etage 12 = 10** (8 von 10),
> **Etage 13 = 10** (11 von 13) — und **Etage 14/15 = 15, also schon korrekt**.
> Betroffen von der Blanko-Änderung sind damit nur 11-13. Für das
> Isolations-Experiment auf Etage 15 ist `unk3` folglich **kein Störfaktor**.
> Werkzeug: `python tools/fix_unk3.py` (Trockenlauf) / `--write`.

### D. Crash-Char-IDs ✔ unsere Whitelist gewinnt

Unverändert: `145` (Screamer) und `148-150` (Grand Savage) laufen bei uns
in-game. Die GitHub-Liste wirft „crasht" und „sieht kaputt aus / ist riesig"
zusammen. Der Ghidra-Zweig liefert dazu nichts Neues, also bleibt es bei
unserer einzeln getesteten Whitelist.

---

## 🔥 NEUER BEFUND: `raw[0]` ist das **Wellen-Feld** — und der Randomizer klonte es mit

Der Decompiler nennt bei `+0x10` ein `s16 wave`: **nur Welle 0 spawnt beim
Betreten der Etage**, 1-3 sind Nachschub, -3 ein Sonderfall. In unserem
Record-Layout ist `+0x10` genau `raw[0]`.

**Gegenprobe über alle 499 Vanilla-Records — 100 % trennscharf, keine Ausnahme:**

| `raw[0]` | Records | x = y = 0 ? |
|---|---|---|
| 0 (Start) | 340 | nein |
| 1 / 2 / 3 (Nachschub) | 18 / 13 / 5 | nein |
| 65533 = **−3** (Sonder) | 123 | **ja, alle** |

Damit ist auch unsere alte Notiz präzisiert: „Reinforcement-Einheiten haben
`x=y=0`, `raw[0]=65533`" beschrieb nur die **Sonder**-Records (−3). Die
echten Nachschubwellen 1-3 stehen auf **normalen Positionen** und waren
dadurch von Start-Gegnern nicht zu unterscheiden.

> **Das war ein echter Bug im Randomizer.** Er klont die Vanilla-Templates
> mitsamt `raw`. Auf den Etagen **5, 6, 9, 23, 24** sind **36 von 376**
> Templates Nachschub-Slots (Etage 24: 12 von 25!). Wurde dort randomisiert,
> stand der Gegner in der Editor-Tabelle, erschien aber **beim Betreten nicht**.
> Das ist eine zweite, bisher unbekannte Ursache für „manche Gegner sehe ich nie".
>
> **Gefixt:** `_randomize_floor` setzt jetzt `raw[0] = 0`.
> Regressionstest: `python tools/test_essential_abil.py`.

---

## 📥 NEUES WISSEN aus dem Repo (bei uns bisher nicht dokumentiert)

1. **Char-ID-Konflikt Partner ↔ Gegner:** Taucht dieselbe `char_id` sowohl in
   `db_party_9XX` (Partner) als auch in `db_dpos_9XX` (Gegner) auf, kann das
   Spiel crashen. → Beim Platzieren prüfen!
2. **Recruit-Aware-Logic:** Das Spiel konvertiert bereits rekrutierte Chars
   automatisch zur Ally-Seite. Passt zu unserem Roster-Flag-Befund und erklärt
   ihn evtl. tiefer.
3. **VS-Mode-Stat-Tabelle** bei `arm9.bin 0xffc56` (= ROM `0x103C56`) aus
   `db_VSstatus.inc` — bei uns bisher nur am Rande erwähnt.
4. **`db_party`-Record-Layout** (14 Bytes: type/level/char_id/…/slot) —
   ergänzt unsere Deploy-Slot-Doku.
5. **Map-Mismatch-Gotcha:** Floor 7 mit Map 15 crasht, Floor 6 mit Map 15 läuft.
   Deckt sich mit unserem Donor-Floor-Problem.

---

## 📤 KORREKTUREN für die Repo-Doku

Falls das Repo gepflegt wird, sollten diese Punkte dort richtiggestellt werden:

1. **dpos Bytes 0-1** sind **nicht** `u16 instance_id`, sondern
   `u8 slot` + `u8 TEAM`. Das TEAM-Byte ist in-game verifiziert
   (`3` = Gegner, `1` = Spieler, `5` = Objekt) — Randomizer-Einheiten mit
   `team=1` spawnten nachweislich im Spielerteam.
2. **dpos `0x0E` „team"** ist bei uns `unk7` und trägt andere Werte;
   das echte Team-Byte liegt bei Byte 1 (s. o.).
3. **Stat-Record:** Der Index-Prüfschlüssel liegt bei unserem `+6`
   (= deren `0x02`), nicht bei `0x00`. Ihre Labels `character_id`/`sprite_id`
   sind vermutlich vertauscht.
4. **Gegner-Cap** ist das 25-Sprite-Limit, kein per-Floor-Hardcode (s. B).

---

## dpos-Record — zusammengeführtes Layout (Stand 2026-10-14)

Links unsere Feldnamen, rechts die aus dem Decompiler. Wo sich beides
widerspricht, steht die Begründung.

| Offset | Lokal | Ghidra | Status |
|---|---|---|---|
| +0x00 | `u8 slot` | Eintrags-Index | gleich |
| +0x01 | `u8 TEAM` (3=Gegner, 1=Spieler, 5=Objekt) | „Art" 0-5 → Aktor-Lager 0-3 | **unsere Lesart gilt** (in-game: `team=1` spawnt im Spielerteam) |
| +0x02 | `u16 char` | `char_id` | gleich |
| +0x04 | `u16 level` | `level` | gleich |
| +0x06 | `u16 unk3` | `u8 ai_mode` | Ghidra genauer; in Vanilla folgenlos (kein Record ≥ 256) |
| +0x07 | — | `u8 Flags` (1 → 0x40000, 2 → 0x1000) | **neu**, in Vanilla immer 0 |
| +0x08 | `u16 x` | `x`, 1-basiert | gleich ✔ |
| +0x0A | `u16 y` | `y`, 1-basiert | gleich ✔ |
| +0x0C | `u16 dir` (0=O,1=N,2=W,3=S) | „in den Aktor, meist 2" | **unsere Lesart gilt** (in-game bestätigt) |
| +0x0E | `u16 unk7` | `team`/Gruppe | Ghidra plausibler (Spawn-Filter nutzt es); Vanilla 1-13 |
| +0x10 | `raw[0]` | **`s16 wave`** | **Ghidra, 100 % verifiziert** (s. o.) |
| +0x12 | `raw[1]` | — | AI-Typ (lokal) |
| +0x14 | `raw[2]` | — | Aggression 0-100 (lokal) |

Merkregel: `raw[n]` liegt bei `+0x10 + 2n`.

---

## Nächste Schritte

1. ~~Branch `claude/ecstatic-dirac-153vh5` auswerten~~ ✔ erledigt 2026-10-14.
2. ~~Punkt A (map_id vs. difficulty) klären~~ ✔ `map_id`. **Zu tun:**
   `REPORT.md` und Memory nachziehen, „difficulty" überall streichen.
3. Punkt C in-game testen: `python tools/fix_unk3.py --mode aktiv --write`
   auf den Etagen 11-13 und prüfen, ob die Gegner aggressiver werden.
4. Punkt B in-game testen (Aktor-Plätze statt Sprites): 30 Gegner mit nur
   10 verschiedenen Charakteren auf eine Etage. Läuft das, ist
   `MAX_UNIQUE_SPRITES` falsch benannt und zu niedrig.
5. Die beiden Wissensbasen zusammenführen — Vorschlag: dieses Repo wird die
   kanonische Quelle, die GitHub-`docs/` werden als `docs/legacy-us/`
   eingegliedert und mit den Korrekturen oben versehen. Der Ghidra-Zweig
   lohnt dabei besonders: seine Toolchain (`tools/re/ghidra/`) ist der
   erste Weg im Projekt, Fragen wie die HP-Formel am **Code** zu klären
   statt am Verhalten — und er läuft headless, also auch in der Cloud,
   sofern die ROM dort liegt.
