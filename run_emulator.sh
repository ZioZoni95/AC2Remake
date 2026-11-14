#!/usr/bin/env bash
# Lancia ZoniStationOne (che resta nel suo repo) montando un disco se fornito.
# Uso: ./run_emulator.sh                 → menu BIOS
#       ./run_emulator.sh game.bin       → BIOS + disco (nome file in ../ZonistationOne/games/)
set -euo pipefail

EMU_ROOT="$HOME/GitHub/ZonistationOne"
BIOS="$EMU_ROOT/roms/SCPH-7502.BIN"

ARGS=("$BIOS")
if [[ $# -ge 1 ]]; then
  ARGS+=("--game=$EMU_ROOT/games/$1")
fi

# GLEW/GLX non parte su Wayland nativo: serve X11 (XWayland).
cd "$EMU_ROOT/run"
SDL_VIDEODRIVER=x11 exec "$EMU_ROOT/ZoniStation_One" "${ARGS[@]}"
