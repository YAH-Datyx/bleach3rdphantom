#!/usr/bin/env bash
# Decompiliert Funktionen an Adressen in arm9 + Overlay N.
#   tools/re/ghidra/decompile.sh <overlay> <out.c> <addr> [addr ...]
# Das Ghidra-Projekt wird in build/ghidra/ zwischengespeichert (gitignored).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
GHIDRA="${GHIDRA_HOME:-/opt/ghidra_11.4.2_PUBLIC}"
OV="$1"; OUT="$2"; shift 2
PROJ="$ROOT/build/ghidra"; NAME="ov$OV"
mkdir -p "$PROJ"
if [ ! -d "$PROJ/$NAME.rep" ]; then
  python3 "$ROOT/tools/re/ghidra/build_image.py" "$OV" "$PROJ/$NAME.bin"
  "$GHIDRA/support/analyzeHeadless" "$PROJ" "$NAME" -import "$PROJ/$NAME.bin" \
    -loader BinaryLoader -loader-baseAddr 0x02000000 -processor ARM:LE:32:v5t \
    -scriptPath "$ROOT/tools/re/ghidra" -postScript DecompileAt.java "$OUT" "$@" 2>&1 | grep -E "ERROR|Exception|DecompileAt" || true
else
  "$GHIDRA/support/analyzeHeadless" "$PROJ" "$NAME" -process "$NAME.bin" -noanalysis \
    -scriptPath "$ROOT/tools/re/ghidra" -postScript DecompileAt.java "$OUT" "$@" 2>&1 | grep -E "ERROR|Exception|DecompileAt" || true
fi
echo "→ $OUT"
