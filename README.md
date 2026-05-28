# Bleach: The 3rd Phantom — Reverse Engineering / Romhack

Reverse-Engineering-Projekt zum Nintendo-DS-Spiel *Bleach: The 3rd Phantom*
(Sega / Tom Create, 2009) mit dem Ziel, Gameplay-Modifikationen
(Stats, Schadensformeln, Story-Skript, Items) vornehmen zu können.

> **Rechtlich:** Dieses Repo enthält **keine** ROM-Daten, keine extrahierten
> Assets und keinen Originalcode des Spiels. Es enthält ausschließlich
> selbst geschriebene Tools, Skripte, Doku und Patches (Diffs).
> Die ROM musst du legal aus deinem eigenen Cartridge dumpen und unter
> `rom/Bleach3rdPhantom.nds` ablegen (wird von `.gitignore` ignoriert).

## Setup

```bash
./tools/setup.sh           # installiert ndstool, dsdecmp, ARM-Toolchain, Python-Deps
./tools/unpack.sh          # entpackt rom/Bleach3rdPhantom.nds nach unpacked/
```

## Verzeichnisstruktur

```
rom/                # Original-ROM (gitignored)
unpacked/           # ndstool -x Output: arm9.bin, arm7.bin, overlays, data/ (gitignored)
build/              # gepatchte ROM (gitignored)
tools/              # Setup + Hilfsskripte (committet)
  setup.sh
  unpack.sh
  repack.sh
  scripts/          # Python-Parser für Custom-Formate
docs/               # Notizen zu Formaten, Memory-Map, Funktionen
  inventory.md      # Filesystem-Inventar
  formats/          # je ein Markdown pro identifiziertem Container
  arm9-notes.md     # RE-Funde aus Ghidra
patches/            # *.xdelta Patches gegen Original-ROM (das ist das, was geteilt wird)
```

## Roadmap (Gameplay-Mod-Fokus)

- [ ] **Phase 1 — Aufbruch**
  - [ ] ROM mit `ndstool -x` entpacken, Filesystem-Inventar erstellen
  - [ ] Container automatisch klassifizieren (NARC/CARC/LZ/Huff/Raw)
  - [ ] DeSmuME mit GDB-Stub zum Laufen bringen
- [ ] **Phase 2 — Daten-Tabellen finden** (für Romhacks meist 80 % des Wertes)
  - [ ] Charakter-Stat-Tabelle lokalisieren (Cheat-Engine-Stil: Wert im RAM finden → Backreference zur ROM-Adresse)
  - [ ] Item-/Skill-Tabelle
  - [ ] Schadensformel-Funktion in ARM9 / Overlay finden
  - [ ] Encounter-/Map-Daten
- [ ] **Phase 3 — Tooling**
  - [ ] Python-Editor für Stat-Tabellen (lesen + schreiben + Repack)
  - [ ] Build-Pipeline: unpacked/ → patched.nds → xdelta gegen Original
- [ ] **Phase 4 — Skript / Text** (für Story-Mods)
  - [ ] Text-Encoding identifizieren (Shift-JIS? Custom?)
  - [ ] NFTR-Schriftarten dumpen / Glyph-Mapping
  - [ ] Skript-Container parsen, Round-Trip (Dump → Edit → Reinject)

## Workflow für eine Änderung

1. Im RAM den Wert finden (DeSmuME RAM-Search), den du ändern willst.
2. Memory-Breakpoint setzen, In-Game den Wert triggern (Kampf etc.).
3. Aus der ARM9-Adresse im Disassembly (Ghidra) die Funktion identifizieren.
4. Datenquelle zurückverfolgen → ROM-Offset bestimmen.
5. Patch schreiben (binär oder via Python-Skript), `repack.sh` ausführen.
6. Testen in DeSmuME, dann `xdelta3` Patch gegen Original generieren → `patches/`.
```
