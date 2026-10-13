#!/usr/bin/env bash
# Decompiliert arm9 komplett und jedes Overlay (nur dessen eigene Funktionen).
#   tools/re/ghidra/decompile_all.sh [overlay ...]     (ohne Angabe: arm9 + alle 25)
# Ausgabe: build/decomp/arm9_*.c, build/decomp/ovNN_*.c, *_index.tsv  (gitignored –
# decompilierter Code stammt aus der ROM und gehoert nicht ins Repo).
# Laufzeit: Analyse je Projekt einige Minuten; JOBS parallel (Standard 2).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
GHIDRA="${GHIDRA_HOME:-/opt/ghidra_11.4.2_PUBLIC}"
PROJ="$ROOT/build/ghidra"; OUT="$ROOT/build/decomp"; S="$ROOT/tools/re/ghidra"
JOBS="${JOBS:-2}"
OVL_LO=0x0215B5A0
mkdir -p "$PROJ" "$OUT"

run_one() {   # $1 = Overlay-Nr; $2 = Praefix; $3/$4 = Bereich
  local ov="$1" prefix="$2" lo="$3" hi="$4" name="ov$1"
  if [ ! -d "$PROJ/$name.rep" ]; then
    python3 "$S/build_image.py" "$ov" "$PROJ/$name.bin" >/dev/null
    "$GHIDRA/support/analyzeHeadless" "$PROJ" "$name" -import "$PROJ/$name.bin" \
      -loader BinaryLoader -loader-baseAddr 0x02000000 -processor ARM:LE:32:v5t \
      -max-cpu 2 -scriptPath "$S" -postScript DecompileAll.java "$OUT" "$prefix" "$lo" "$hi" "$S/names.txt" \
      > "$OUT/$prefix.log" 2>&1
  else
    "$GHIDRA/support/analyzeHeadless" "$PROJ" "$name" -process "$name.bin" -noanalysis \
      -scriptPath "$S" -postScript DecompileAll.java "$OUT" "$prefix" "$lo" "$hi" "$S/names.txt" \
      > "$OUT/$prefix.log" 2>&1
  fi
  grep -h "DecompileAll .*Funktionen" "$OUT/$prefix.log" || echo "$prefix: FEHLER, siehe $OUT/$prefix.log"
}

if [ $# -eq 0 ]; then
  run_one 1 arm9 0x02000000 "$OVL_LO"        # arm9 einmal (aus dem Projekt mit Overlay 1)
  set -- $(seq 0 24)
fi
for ov in "$@"; do
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 5; done
  run_one "$ov" "$(printf 'ov%02d' "$ov")" "$OVL_LO" 0x02200000 &
done
wait
echo "→ $OUT"
