#!/usr/bin/env bash
# Installiert die Toolchain für DS-Romhacking.
# Getestet auf Debian/Ubuntu. Idempotent.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/tools/bin"
VENDOR="$ROOT/tools/vendor"
mkdir -p "$BIN" "$VENDOR"

need_root() { if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; else SUDO=""; fi; }
need_root

echo "== APT-Pakete =="
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
    build-essential git wget curl unzip p7zip-full \
    python3 python3-pip python3-venv \
    xdelta3 \
    gcc-arm-none-eabi binutils-arm-none-eabi \
    libpng-dev zlib1g-dev

echo "== Python venv =="
python3 -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install --upgrade pip
pip install ndspy lz77 pillow tabulate

echo "== ndstool (devkitPro-Quelle, ohne devkitPro-Installer) =="
if [ ! -x "$BIN/ndstool" ]; then
  git clone --depth 1 https://github.com/devkitPro/ndstool "$VENDOR/ndstool"
  ( cd "$VENDOR/ndstool" && ./autogen.sh && ./configure && make -j"$(nproc)" )
  cp "$VENDOR/ndstool/ndstool" "$BIN/ndstool"
fi

echo "== dsdecmp (LZ/Huff/RLE) =="
if [ ! -x "$BIN/dsdecmp" ]; then
  git clone --depth 1 https://github.com/Barubary/dsdecmp "$VENDOR/dsdecmp" || true
  # dsdecmp ist .NET — als Fallback nutzen wir ndspy's Compression in Python.
  echo "Hinweis: dsdecmp ist .NET-basiert. Wir nutzen primär ndspy (Python) für LZ/Huff."
fi

echo "== Fertig. Aktiviere venv mit: source .venv/bin/activate =="
