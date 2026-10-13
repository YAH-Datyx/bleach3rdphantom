# Tower-Floor-Ablauf & Spawn-Logik (Overlay 1)

Ermittelt mit Ghidra 11.4.2 (headless) aus arm9 + Overlay 1 der ROM YBTP. Werkzeug:
`tools/re/ghidra/decompile.sh 1 build/re/out.c <adresse> ...`. Der
decompilierte Code bleibt lokal in `build/` (gitignored). Hier steht nur unsere
Beschreibung des Verhaltens.

## Floor-Zustandsmaschine — `FUN_02189A58` (Overlay 1)

Liest die aktuelle Floor-Nummer aus dem Spielzustand und holt per
`GetTowerFloor` (`0x020570E4`) den Tower-Eintrag. Danach läuft sie über einen
Schritt-Zähler:

| Schritt | Aktion |
|---|---|
| 0 | Map laden: `FUN_0217E5D4(ctx, tower.map_id)` |
| 1 | warten, bis die Map geladen ist |
| 3 | Gegnerdatei laden: `FUN_0217A8EC(ctx, 900 + floor)` → `"/yamada/DataBase/db_dpos_%03d.narc"` (Nummer im Zustand bei `+0x4E84`) |
| 4 | warten, bis geladen, dann **Spawn**: `FUN_02182068(ctx, -1, -1, 0, 0)` |
| 5 | Aktoren initialisieren (32 Plätze) |

`FUN_02189E88` (zweiter Tower-Aufrufer): Liegt ein Fortschrittswert im
Spielzustand (`+0x4C54`) über 89, wird `tower.floor_echo` (Feld +4) in ein
anderes Objekt übernommen. **floor_echo ist also eine eigene ID**, kein
Duplikat. Bedeutung noch offen (BGM/Szenario?).

## Spawn — `FUN_02182068(ctx, team, side, wave, posCheck)`

1. Die bis zu **8 Party-Mitglieder** werden zuerst in die Aktor-Tabelle eingetragen.
2. Danach läuft eine Schleife über die dpos-Einträge (54 Byte), **höchstens 64 Einträge** (Abbruch nach Index 63).
3. Ein Eintrag spawnt nur, wenn alle Bedingungen gelten:
   - `char_id != 0`
   - `char_id` ist nicht wegen eines Spielflags ausgeschlossen (Flag aus ⇒ 22 und 26 ausgeschlossen, Flag an ⇒ 21 und 27 ausgeschlossen; vermutlich die Protagonisten-Variante)
   - **`wave` (+0x10) == Parameter `wave`**: Der Tower-Start übergibt 0
   - bei `team != -1`: Feld +0x0E == team
   - Filter nach Byte +1 (Art) gegen den `side`-Parameter
4. Jeder Spawn braucht einen freien der **32 Aktor-Plätze** (je 0x13C Bytes). Sind alle belegt, erscheint der Gegner nicht.

### dpos-Eintrag, neu verstanden

| Offset | Typ | Bedeutung |
|---|---|---|
| +0x00 | u8 | Eintrags-Index; wird an `FUN_0218200C` übergeben (Override-Daten) |
| +0x01 | u8 | Art: 0–5. Bei Gegnern 3, bei Sonder-Spawns 5. Wird auf das Aktor-Lager 0/1/2/3 abgebildet |
| +0x02 | u16 | char_id |
| +0x04 | u16 | level |
| +0x06 | u8 | „ai_mode“, wird als Festkomma (`<<12`) an `FUN_020A2688` übergeben, Werte 10/15 |
| +0x07 | u8 | Flags: 1 → Aktor-Flag 0x40000, 2 → 0x1000 |
| +0x08/+0x0A | u16 | x/y, 1-basiert (das Spiel zieht 1 ab) |
| +0x0C | u16 | wird in den Aktor übernommen (meist 2) |
| +0x0E | u16 | team/Gruppe |
| +0x10 | s16 | **wave**: 0 = beim Start; 1, 2, 3 = Nachschub; -3 = Sonder (oft zusammen mit Art 5) |

## Folgerungen für Mods

Es gibt **keine hardcodierte Grenze pro Floor**. Die beobachteten Limits
kommen von drei allgemeinen Regeln:

1. **Nur Welle 0 spawnt beim Betreten.** Floor 9 (Kopie von 930) hat 8 Einträge
   in Welle 0 und 5 in Welle 1. Das ergibt die beobachteten ~13 Gegner, wenn
   Welle 1 nachkommt.
2. **32 Aktor-Plätze minus Party (bis zu 8) ⇒ höchstens ~24 Gegner gleichzeitig.**
   Das passt zu den ~24 auf Floor 5.
3. **Nur die ersten 64 dpos-Slots** werden überhaupt gelesen.

Konsequenzen:
- Mehr Gegner am Start: `wave` vorhandener Einträge auf 0 setzen, maximal ~24.
- Für mehr als 24 müsste das Aktor-Array (32 × 0x13C) vergrößert werden. Das ist
  ein Code- und Speicherpatch, also aufwendig.
- Neu angelegte Slots blieben vermutlich unsichtbar, weil `wave`, die Art (+1) oder
  Position und Index aus dem geklonten Template nicht passten. Prüfen.

`gamedata.py` exportiert `wave` jetzt, und `validate` warnt vor Slots ab 64 und
vor mehr als 24 Gegnern in Welle 0.

## Offen

- Wann und wie spawnen die Wellen 1–3 und -3 (Trigger)?
- **Floor-7-Crash:** In der gemoddeten ROM hat Floor 7 14 Gegner in Welle 0
  und keine Auffälligkeit in den Daten. Als Nächstes sind `floor_echo` (7 → ?) und
  Map-spezifische Ereignisse zu prüfen.
