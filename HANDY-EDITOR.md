# Editor auf dem iPhone (Pythonista / Pyto / a-Shell)

Der PC-Editor (tkinter) läuft NICHT auf iOS. Aber `iphone_editor.py` ist
eine **einzige, eigenständige Python-Datei ohne Abhängigkeiten** — sie
läuft in einer iOS-Python-App und bearbeitet die `.nds` direkt.

## Welche App?
- **Pyto** (App Store, kostenlos) — empfohlen, guter Datei-/iCloud-Zugriff.
- **a-Shell** (kostenlos) — Terminal mit Python, iCloud-Zugriff via
  `pickFolder`. Auch gut.
- **Pythonista 3** (~11 €) — sehr ausgereift.

## Einrichtung (einmalig)
1. `iphone_editor.py` in die iCloud legen (liegt schon im Projektordner;
   der PC-Editor spiegelt den Projektordner ohnehin über OneDrive — die
   Datei bei Bedarf zusätzlich in `iCloudDrive/Modded ROM files/` kopieren).
2. In der Python-App die Datei öffnen/importieren:
   - **Pyto:** „+" → Datei aus iCloud importieren → `iphone_editor.py`.
   - **a-Shell:** die Datei in den a-Shell-Ordner legen (Dateien-App).
3. Die **ROM** muss für die App erreichbar sein. Zwei Wege:
   - **A) ROM neben das Skript legen:** die `Bleach3P modded.nds` in den
     gleichen App-Ordner wie `iphone_editor.py` — wird automatisch gefunden.
   - **B) Pfad setzen:** oben im Skript `ROM_PATH = '...'` auf den vollen
     Pfad der `.nds` setzen (z. B. den iCloud-Pfad, den die App anzeigt).

## Ablauf beim Spielen/Editieren
```
1. iPhone-Shortcut: ROM aus iCloud -> Python-App-Ordner (falls Weg A)
2. iphone_editor.py in der App starten -> Menü:
     1) Etage anzeigen
     2) Etage randomisieren (Level + Anzahl)
     3) Skillpoints einer Etage setzen
     4) GOD-MODE Etage (Lv91-99)
     0) Beenden  (ROM ist gespeichert)
3. iPhone-Shortcut: bearbeitete ROM -> iCloud -> DeSmuME-Ordner (Replace)
4. In DeSmuME spielen.
```

## Was der Mobil-Editor kann / nicht kann
KANN: Etage anzeigen, randomisieren (Level ±5, Anzahl, begehbare Felder,
Blick zur Deploy-Zone, Sprite-Limit 25, Riesen/NONCOM/Blacklist raus),
Skillpoints pro Etage (db_result + ARM9-Zwilling), GOD-MODE (Lv91-99).
NICHT (dafür PC-Editor): starke Stat-Boosts, AI-Skill-Editor, Map-Wechsel,
Char-Designer, Kampagne, klickbare Karte. Der Mobil-Editor ist für
schnelle Änderungen unterwegs — der PC-Editor bleibt das volle Werkzeug.

## Sicherheit
Der Mobil-Editor schreibt DIREKT in die ROM (kein Auto-Backup auf dem
Handy!). Vor größeren Aktionen unterwegs am besten einmal die ROM im
Dateien-App kopieren. Am PC ist `Bleach3P_test_mod.nds` die Vanilla-
Referenz zum Wiederherstellen.
