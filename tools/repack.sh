#!/usr/bin/env bash
# Baut aus unpacked/ wieder eine .nds und erzeugt einen xdelta-Patch gegen Original.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/unpacked"
ORIG="${1:-$ROOT/rom/Bleach3rdPhantom.nds}"
OUT="$ROOT/build/Bleach3rdPhantom.patched.nds"
mkdir -p "$ROOT/build"

"$ROOT/tools/bin/ndstool" -c "$OUT" \
  -9 "$SRC/arm9.bin" -7 "$SRC/arm7.bin" \
  -y9 "$SRC/y9.bin" -y7 "$SRC/y7.bin" \
  -d "$SRC/data" -y "$SRC/overlay" \
  -t "$SRC/banner.bin" -h "$SRC/header.bin"

xdelta3 -e -s "$ORIG" "$OUT" "$ROOT/build/patch.xdelta"
echo "ROM: $OUT"
echo "Patch: $ROOT/build/patch.xdelta"
