#!/usr/bin/env bash
# Entpackt die ROM nach unpacked/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROM="${1:-$ROOT/rom/Bleach3rdPhantom.nds}"
OUT="$ROOT/unpacked"

if [ ! -f "$ROM" ]; then
  echo "ROM nicht gefunden: $ROM"
  echo "Lege die gedumpte ROM unter rom/Bleach3rdPhantom.nds ab."
  exit 1
fi

mkdir -p "$OUT"
"$ROOT/tools/bin/ndstool" -x "$ROM" \
  -9 "$OUT/arm9.bin" \
  -7 "$OUT/arm7.bin" \
  -y9 "$OUT/y9.bin" \
  -y7 "$OUT/y7.bin" \
  -d  "$OUT/data" \
  -y  "$OUT/overlay" \
  -t  "$OUT/banner.bin" \
  -h  "$OUT/header.bin"

echo "Entpackt nach $OUT"
echo "Nächster Schritt: python3 tools/scripts/inventory.py"
