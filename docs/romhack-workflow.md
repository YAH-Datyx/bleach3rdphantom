# Romhack-Workflow: Vom RAM-Wert zur ROM-Änderung

Konkrete Schritt-für-Schritt-Anleitung für Gameplay-Mods (Stats, Schaden, Items).

## 1. RAM-Wert finden (Cheat-Engine-Stil)

DeSmuME bietet einen RAM-Search:
1. Spiel starten, in einen Kampf gehen, HP eines Charakters notieren (z. B. 120).
2. **Tools → RAM Search → Search**: Wert `120`, Datentyp `2 bytes` oder `4 bytes`.
3. Im Spiel HP ändern (Treffer kassieren → 95), erneut suchen mit neuem Wert.
4. Nach 2–3 Iterationen bleiben wenige Kandidaten. → **DTCM/Main-RAM-Adresse** notieren.

## 2. Memory-Breakpoint setzen

DeSmuME mit GDB-Stub starten:
```bash
desmume --arm9gdb=20000 rom/Bleach3rdPhantom.nds
arm-none-eabi-gdb -ex "target remote :20000" unpacked/arm9.elf
(gdb) watch *0x02XXXXXX
```
Im Spiel den Wert nochmal verändern (Treffer) → GDB hält an.
PC notieren (= ARM9-Adresse, die geschrieben hat).

## 3. In Ghidra zur Funktion springen

`unpacked/arm9.bin` in Ghidra laden (Loader: Raw, ARM v5T LE, Basisadresse aus
`header.bin` lesen — meist `0x02000000`). Overlays separat laden, Basisadressen
stehen in `y9.bin` (Overlay-Tabelle).

→ Funktion identifizieren, die den Wert berechnet (Schadensformel, Stat-Lookup).

## 4. Datenquelle finden

Meist liest die Funktion aus einer Tabelle:
- Stat-Tabelle: Array of Struct, Index = CharakterID.
- In Ghidra: Cross-References zur Lese-Adresse folgen → Basis-Pointer →
  ROM-Offset.

## 5. Ändern

Zwei Wege:
- **Daten-Patch**: Byte in `unpacked/data/.../stats.bin` ändern, neu packen.
- **Code-Patch**: ARM-Instruktion in `arm9.bin` ändern (z. B. `mov r0, #99`),
  ARM9-Encryption beachten — ndstool kümmert sich beim Repack normalerweise.

## 6. Build & Test

```bash
./tools/repack.sh
desmume build/Bleach3rdPhantom.patched.nds
```

## 7. Patch teilen

`build/patch.xdelta` ist die rechtlich saubere Form, Änderungen zu verteilen —
sie enthält keinen Originalcode.

## Tipps speziell für Bleach: The 3rd Phantom

- Engine ist von Tom Create (gleicher Entwickler wie *Bleach: Dark Souls*).
  Falls für Dark Souls schon RE-Notizen existieren, lohnt ein Vergleich der
  Datenstrukturen — Tom Create recycelt viel.
- SRPG/Grid-Battle → Encounter-Daten und Map-Layouts sind separate Container,
  oft pro Mission eine NARC.
- Texte sind japanisch (Shift-JIS) bzw. in der US-Version ASCII/UTF-8-artig
  mit Custom-Control-Codes für Farbe/Portrait — beim Mod nicht relevant außer
  du willst Skript anfassen.
