# apps – veröffentlichte Artifacts (Quellcode)

Beide Seiten enthalten **keine** ROM-Daten. Die ROM wählt man im Browser aus,
sie wird nur lokal gelesen.

| App | Was | Veröffentlichen |
|---|---|---|
| `seelenturm/index.html` | Eigener Tower-Taktik-Nachbau: Titel → Turm → Team → Kampf. Etagen, Gegner, Wellen und Werte liest er aus der ROM, Grafik und Regeln sind eigene Platzhalter | Datei direkt als Artifact veröffentlichen |
| `taschenkonsole/` | DS-Emulator (EmulatorJS + melonDS/DeSmuME, GPL-3.0) für die eigene `.nds` | `python3 apps/taschenkonsole/build.py`, dann `build/taschenkonsole/` veröffentlichen |

Getestet: lokal in Chromium (Playwright). Auf dem Handy und in der Claude-App ist nichts getestet.
