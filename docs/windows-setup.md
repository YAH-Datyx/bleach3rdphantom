# Setup unter Windows (Laptop & Heim-PC)

`setup.sh` ist ein Bash-Skript und braucht eine Linux-Umgebung. Unter Windows
nutzen wir **WSL2** (Windows Subsystem for Linux). Damit läuft das Build-/
Unpack-Tooling in Linux, während du DeSmuME und Ghidra ganz normal als
Windows-Programme verwendest und auf die gleichen Dateien zugreifst.

## 1. WSL2 + Ubuntu installieren (einmalig pro Maschine)

PowerShell **als Administrator** öffnen und ausführen:

```powershell
wsl --install -d Ubuntu
```

Danach Neustart. Beim ersten Start von Ubuntu legst du einen Linux-Benutzer
mit Passwort an (kann anders sein als dein Windows-User).

Test:

```powershell
wsl --status        # sollte WSL2 als Default zeigen
wsl -l -v           # zeigt installierte Distros mit Version
```

Falls Version 1 angezeigt wird:

```powershell
wsl --set-version Ubuntu 2
wsl --set-default-version 2
```

## 2. Repo clonen — wichtig: **im Linux-Dateisystem**, nicht unter `/mnt/c/`

Unter WSL liegt dein Windows-Laufwerk unter `/mnt/c/`. Auf Dateien dort
zuzugreifen ist **stark verlangsamt** (10–100× langsamer für `git`/`make`).
Deshalb clonen wir im Linux-Home:

In Ubuntu (Start-Menü → „Ubuntu" oder `wsl` in PowerShell):

```bash
cd ~
git clone https://github.com/YAH-Datyx/bleach3rdphantom.git
cd bleach3rdphantom
git checkout claude/nice-volta-9kI3i
```

## 3. setup.sh ausführen

```bash
./tools/setup.sh
```

Das Skript fragt einmal nach deinem Linux-Passwort (für `sudo apt install`).
Dauer: ~5–10 Minuten, je nach Verbindung.

## 4. ROM ablegen

Du kannst die ROM bequem aus dem Windows-Explorer ins Linux-Dateisystem
kopieren. WSL2 mountet dein Linux-Home unter:

```
\\wsl$\Ubuntu\home\<dein-linux-user>\bleach3rdphantom\rom\
```

Diesen Pfad einfach in die Explorer-Adresszeile kleben → ROM nach `rom/`
ziehen (Datei muss `Bleach3rdPhantom.nds` heißen, sonst beim Aufruf den
Pfad mit übergeben).

## 5. Entpacken

```bash
./tools/unpack.sh
source .venv/bin/activate
python3 tools/scripts/inventory.py
```

Anschließend findest du das Inventar unter `docs/inventory.md`.

## 6. Windows-Tools dazu

Diese installierst du **nativ unter Windows** (nicht in WSL — die haben
GUIs und laufen so flüssiger):

| Tool       | Zweck                          | Quelle                                  |
|------------|--------------------------------|-----------------------------------------|
| DeSmuME    | Emulator + RAM-Search          | https://desmume.org/                    |
| Ghidra     | Disassembler (ARM9/ARM7)       | https://ghidra-sre.org/                 |
| Tinke      | DS-Asset-Browser (GUI)         | https://github.com/pleonex/tinke        |
| HxD        | Hex-Editor                     | https://mh-nexus.de/de/hxd/             |

Alle können die Dateien aus deinem WSL-Linux-Home öffnen — einfach den
`\\wsl$\Ubuntu\...`-Pfad benutzen oder die Datei nach Windows kopieren.

## Workflow zwischen Laptop und Heim-PC

Da das Repo auf GitHub liegt, syncst du Änderungen an Tools/Skripten/Doku
via `git push` / `git pull`. Die ROM selbst wandert **nicht** durch git
(steht in `.gitignore`) — die musst du auf jeder Maschine separat in
`rom/` ablegen.

```bash
# vor dem Arbeiten:
git pull
# nach Änderungen:
git add -A && git commit -m "..." && git push
```

## Troubleshooting

- **`wsl --install` schlägt fehl**: Virtualisierung im BIOS aktivieren
  (Intel VT-x / AMD-V), und „Windows-Subsystem für Linux" + „Plattform für
  virtuelle Computer" in „Windows-Features" anhaken.
- **`./tools/setup.sh: Permission denied`**: `chmod +x tools/*.sh`.
- **`apt: command not found`**: Du bist nicht in Ubuntu, sondern in
  PowerShell. Erst `wsl` eingeben.
- **Sehr langsame Builds**: Du arbeitest unter `/mnt/c/...`. Clone das
  Repo in `~/` (Linux-Home) neu.
