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

Zweiter Branch im Repo: `claude/ecstatic-dirac-153vh5` (noch nicht ausgewertet).

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

## ⚠️ OFFENE WIDERSPRÜCHE (noch zu klären)

### A. Feld `0x02` der Tower-Tabelle: „map_id" oder „difficulty"?

- **GitHub:** `map_id` (Map-/Encounter-ID)
- **Unser Memory:** `difficulty` (0-39, soll Level-Scaling beeinflussen)

**Einschätzung: „map_id" ist vermutlich richtig.** Unser Projekt hat
Map-Wechsel *in-game verifiziert*, indem genau dieses Feld gepatcht wurde
(Etage 1 → Hafen-Map). Die „Difficulty"-Deutung stammt aus einer frühen
Vermutung und wurde nie bewiesen. **Zu tun:** Memory/REPORT korrigieren,
falls sich das bestätigt.

### B. Gegner-Obergrenze pro Etage

- **GitHub (Session 4):** Anzahl sichtbarer Gegner sei **hardcoded im arm9 pro
  Floor-Index**; zusätzliche dpos-Slots würden ignoriert.
- **Lokal (bisektiert, in-game):** Zusätzliche Slots **funktionieren** — Etage 1
  läuft sauber mit 25 Gegnern auf den Slots 16-40. Grenze ist die Zahl
  **unique Sprites** (25 ok, 26 = Crash), nicht der Floor-Index.

**Einschätzung: unsere Version ist belastbarer** (neuer, sauber bisektiert, mit
zwei verschiedenen Charaktersätzen gegengeprüft). Die GitHub-Beobachtung hat
vermutlich das Sprite-Limit als Floor-Cap fehlgedeutet.

### C. `unk3` (dpos-Feld bei `+6`) = „ai_mode"?

- **GitHub:** `ai_mode` — `15` = passiv/patrol, `10` = aktiv/boss
- **Lokal:** Bedeutung unbekannt; sicher **kein** Stat-/HP-Flag (bewiesen)

Korrelationstest über alle 30 Vanilla-Etagen: `unk3` korreliert **nicht** sauber
mit `raw[1]` (AI-Typ) / `raw[2]` (Aggression) — bei jedem `unk3`-Wert ist
`(0,0)` die häufigste raw-Kombination. Verteilung:

| unk3 | Vorkommen |
|---|---|
| 10 | 262× (klar häufigster Wert) |
| 15 | 80× |
| 18 | 69× |
| 0 | 38× |
| 13 | 19× |
| 17 | 1× |

**Status: plausible, aber UNBESTÄTIGTE Hypothese.** Dass es ein
*Verhaltens*-Feld ist, passt immerhin dazu, dass es nachweislich kein
Stat-Feld ist.

> ⚠️ **Praktische Folge:** Auf den Kampagnen-Etagen 11-15 wurde `unk3` pauschal
> auf 15 gesetzt (basierend auf einer inzwischen widerlegten HP-Theorie).
> Falls GitHub recht hat, wurden die Gegner damit von „aktiv/boss" auf
> „passiv/patrol" umgestellt — also **passiver gemacht**. Das würde erklären,
> falls sie sich im Test zurückhaltend verhalten. Vanilla-Werte wären:
> Etage 11 = 13, Etage 12/13 = meist 10, Etage 14/15 = 15.

### D. Crash-Char-IDs

- **GitHub:** IDs `175, 195, 100, 145-150` crashen („Filler-Chars")
- **Lokal:** `145` (Screamer) ist in der batch-verifizierten Whitelist und läuft;
  `148-150` (Grand Savage) laufen ebenfalls, sind nur wegen ihrer Größe
  (4 Felder) aus dem Randomizer ausgeschlossen

**Einschätzung:** Die GitHub-Liste wirft vermutlich „crasht" und „sieht kaputt
aus / ist riesig" zusammen. Unsere Whitelist ist einzeln in-game getestet.

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

## Nächste Schritte

1. Branch `claude/ecstatic-dirac-153vh5` auswerten — evtl. weiteres Wissen.
2. Punkt A (map_id vs. difficulty) klären und Memory/REPORT korrigieren.
3. Punkt C testen: `unk3` auf den Kampagnen-Etagen auf Vanilla-Werte
   zurücksetzen und prüfen, ob die Gegner aggressiver werden.
4. Die beiden Wissensbasen zusammenführen — Vorschlag: dieses Repo wird die
   kanonische Quelle, die GitHub-`docs/` werden als `docs/legacy-us/`
   eingegliedert und mit den Korrekturen oben versehen.
