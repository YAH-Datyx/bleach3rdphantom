# Handy ⇄ PC Spielstand-Sync (iCloud)

Der Spielstand (`.dsv`) soll in BEIDE Richtungen wandern. ROM geht nur
PC → Handy (bearbeitet wird nur am PC).

```
        PC (Editor + DeSmuME)                 iPhone (DeSmuME)
   Bleach3P_RE\...\Battery\*.dsv   <----->   App-Battery-Ordner
              │  ▲                              │  ▲
   (push:     │  │  (pull: "DSV vom Handy       │  │  (Shortcuts)
    Watcher/  │  │   holen"-Button/.bat)        │  │
    Editor)   ▼  │                              ▼  │
        iCloudDrive\Modded DSV files\Bleach3P modded.dsv
        iCloudDrive\Modded ROM files\Bleach3P modded.nds
```

## PC → Handy (schon fertig)
- Editor spiegelt ROM + Save beim Speichern automatisch in die iCloud.
- Hintergrund-Watcher `iCloud-Sync starten.bat` spiegelt auch reine
  In-Game-Saves (auch wenn der Editor zu ist).
- **Am Handy:** deine bestehenden iPhone-Shortcuts holen ROM + DSV aus
  der iCloud in den DeSmuME-Ordner (Replace).

## Handy → PC (NEU)
Zwei Schritte:

**1) iPhone-Shortcut: DSV vom Handy in die iCloud legen**
(einmal einrichten — das kann ich nicht für dich bauen, aber hier die
genauen Bausteine für die Kurzbefehle-App:)
- Aktion **„Datei abrufen"** (Get File):
  Ordner = DeSmuME-Battery-Ordner der App
  (Dateien-App → „Auf meinem iPhone" → DeSmuME → Battery →
  `Bleach3P modded.dsv`). „Ordner anzeigen" aus, direkt die Datei wählen.
- Aktion **„Datei speichern"** (Save File):
  Ziel = `iCloud Drive / Modded DSV files`
  „Beim Speichern fragen" **AUS**, „Überschreiben, falls vorhanden" **AN**,
  Dateiname = `Bleach3P modded.dsv`.
- Diesen Shortcut nach dem Spielen einmal tippen (oder als Automation beim
  Schließen von DeSmuME auslösen).

**2) PC: den Stand aus der iCloud in den Battery-Ordner holen**
Drei Wege — alle machen dasselbe:
- **Editor-Button „DSV vom Handy holen"** (Kopfzeile) ← am bequemsten
- **Doppelklick** auf `DSV vom Handy holen.bat`
- **Per Tastendruck:** Rechtsklick auf die .bat → *Verknüpfung erstellen*
  → Verknüpfung → Eigenschaften → Feld *Tastenkombination* (z. B.
  `Strg+Alt+H`) → OK. Dann global per Hotkey.

### Sicherheit (eingebaut)
- Vor dem Überschreiben wird der bisherige PC-Stand nach
  `saves/_vom_handy_backup/` gesichert (mit Zeitstempel).
- Ist der **PC-Stand neuer** als der Handy-Stand (du hast zuletzt am PC
  gespielt), warnt das Tool und holt NICHT automatisch — du bestätigst
  dann bewusst (Button) bzw. nutzt `--force` (.bat/CLI). So geht kein
  Fortschritt verloren.

> Nach dem Holen: DeSmuME am PC neu starten, „Continue" → du spielst mit
> dem Handy-Stand weiter.

## Konflikt-Regel (wichtig)
Immer nur auf EINEM Gerät weiterspielen und dann syncen. Wenn du auf
beiden Geräten seit dem letzten Sync gespielt hast, gibt es zwei
divergierende Stände — dann entscheidet die Zeitstempel-Warnung, welcher
neuer ist; den anderen findest du im Backup-Ordner.
