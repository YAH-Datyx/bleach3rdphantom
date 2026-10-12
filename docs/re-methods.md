# NDS Reverse Engineering: Methoden & Toolchain (Stand 10/2026)

Recherche-Ergebnis: Mit welchen Werkzeugen wir *The 3rd Phantom* vollständig
erschließen. Die Tools sind nach Aufgabe gruppiert.

## 1. Code: ARM9/ARM7 + Overlays

| Tool | Zweck | Warum |
|---|---|---|
| **ds-decomp (`dsd`)** – github.com/AetiasHax/ds-decomp | `rom extract`, `init` (Funktionsgrenzen, Symbole, Relocations für arm9 + alle Overlays), `delink` → ELF, `objdiff`-Config | Aktueller Standard für DS-Decomp-Projekte. Liefert sauber getrennte Funktionen auch in Overlays, das ist die Basis für alles Weitere |
| **Ghidra + NTRGhidra** – github.com/pedro-javierf/NTRGhidra | Lädt `.nds` direkt, setzt Speicherbereiche, das Plugin lädt Overlays dynamisch | Decompiler nach Pseudo-C für die Funktionen, die uns interessieren (Schaden, KI, Spawn-Cap) |
| Ghidra headless (`analyzeHeadless`) | Analyse + Pseudo-C-Export per Skript | läuft auch in dieser Cloud-Umgebung, ohne GUI |
| ndsdisasm / objdiff / decomp.me | Matching-Decomp | erst relevant für Weg C (volle Decompilation) |

Konkrete Ziele im Code:
- Wer liest die Tower-Tabelle `0x020F3B58`? (bekannter Kandidat `0x57114`). Darüber finden wir die Spawn-Cap pro Floor und die Ursache des Floor-7-Crashs.
- Wer liest die Stat-Tabelle `0x020FD882`? Darüber finden wir die Level-Skalierung und die Schadensformel.
- Was bedeuten `ai_mode` und `team` bei den Gegnern? Darüber finden wir die KI.

## 2. Dynamische Analyse: Debugger

| Tool | Stärke |
|---|---|
| **No$gba Debug-Version** (Windows) | Bester DS-Debugger: Read-/Write-Breakpoints, Disassembly, VRAM/OAM-Viewer. Klassische Methode: Write-Breakpoint auf HP-Adresse → Schadensfunktion |
| **DeSmuME dev+-Build** | RAM-Search, `--arm9gdb=PORT` GDB-Stub → Ghidra oder `arm-none-eabi-gdb` anhängen. Der Release-Build hat keine funktionierenden Memory-Breakpoints (siehe session-findings.md) |
| melonDS | Genaueste Emulation, hat inzwischen GDB-Unterstützung. Gut, um Crashes gegenzuprüfen |

Typischer Ablauf: Wert im RAM finden → Write-Breakpoint → PC notieren → in
Ghidra die Funktion benennen → zurück zur Tabelle oder Formel.

## 3. Assets

| Format | Tool |
|---|---|
| Dateisystem, NARC, LZ10/LZ11/Huffman | `ndstool`, **ndspy** (Python; das nutzen unsere Skripte) |
| NCLR/NCGR/NCER/NANR/NSCR (2D-Sprites, BGs, Animationen) | **NitroPaint** (Editor, (de)komprimiert automatisch), **Tinke** / tinke-ultimate / TinkeDSi (Viewer/Export) |
| NSBMD/NSBTX (3D/Texturen) | NitroPaint, Tinke |
| SDAT (Sound) | ndspy.soundArchive, VGMTrans |
| Texte/Fonts (NFTR) | Tinke; das Skriptformat ist spielspezifisch und muss per Hex und Code analysiert werden |

## 4. Übergabe ROM bzw. Tool-Ergebnisse → Claude

**Bevorzugt: die ROM selbst.** Damit kann ich hier `dsd`, Ghidra headless und
ndspy laufen lassen und alles reproduzierbar skripten. Die ROM wird nie
committet (`*.nds` ist in `.gitignore`). Übergabe zum Beispiel per Google-Drive-Datei,
die ich über den Drive-Connector in die Sitzung lade, nach `rom/Bleach3rdPhantom.nds`.
Nur eine selbst gedumpte ROM verwenden.

**Alternative: Tool-Ergebnisse, wenn die ROM nicht geteilt werden soll:**

| Was | Wie erzeugen | Wofür |
|---|---|---|
| `unpacked/`-Ordner (zip) | `./tools/unpack.sh` | Alle Daten- und Code-Analysen |
| `arm9.bin`, `y9.bin`, `overlay/` | Teil von `unpacked/` | Code-RE (Ghidra/dsd) |
| Datei-Inventar | `python3 tools/scripts/inventory.py` | erster Überblick ohne Binärdaten |
| RAM-Dumps (4 MB Main-RAM) vor/nach einer Aktion | DeSmuME/No$gba „Dump memory" | Struct-Layout zur Laufzeit, Diffing |
| Breakpoint-PC + Register-Screenshot | No$gba / DeSmuME dev+ | Funktion finden, die z. B. HP schreibt |
| Savestate + Beschreibung „was passiert gerade" | Emulator | Crashes (Floor 7) reproduzieren |
