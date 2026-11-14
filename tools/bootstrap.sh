#!/usr/bin/env bash
# Ricostruisce l'ambiente su una macchina nuova. Non copia BIOS né disco (non sono in git): li controlla.
# Uso:  ./tools/bootstrap.sh            (dalla radice di AC2Remake, o da dove l'hai clonato)
set -euo pipefail

BASE="$HOME/GitHub"
EMU="$BASE/ZonistationOne"
mkdir -p "$BASE"

if [[ ! -d "$EMU/.git" ]]; then
  git clone https://github.com/ZioZoni95/ZonistationOne.git "$EMU"   # repo privato/pubblico: serve l'accesso git
fi
cd "$EMU"
git fetch origin
git checkout master && git pull --ff-only   # master contiene emu.write_* (commit c59eb77)
if command -v make >/dev/null; then make -j"$(nproc)" || echo "ATTENZIONE: build fallita, vedi il README dell'emulatore (SDL3, glew...)"; fi

echo
echo "=== controllo file non versionati ==="
[[ -f "$EMU/roms/SCPH-7502.BIN" ]] && echo "OK  BIOS PAL" || echo "MANCA  $EMU/roms/SCPH-7502.BIN  (copiala a mano)"
[[ -f "$EMU/games/Ace Combat 2 (Europe).bin" ]] && echo "OK  disco AC2" || echo "MANCA  $EMU/games/Ace Combat 2 (Europe).bin  (copia il .bin)"
[[ -x "$EMU/ZoniStation_One" ]] && echo "OK  emulatore compilato" || echo "MANCA  il binario ZoniStation_One"

echo
echo "=== strumenti ==="
for c in python3 mipsel-linux-gnu-objdump godot unityhub java; do
  command -v "$c" >/dev/null && echo "OK  $c" || echo "MANCA  $c"
done
[[ -x "$HOME/Tools/ghidra/support/analyzeHeadless" ]] && echo "OK  ghidra" || echo "MANCA  ghidra  (./tools/install_re_tools.sh)"
echo
echo "Poi: leggi docs/CONTESTO.md e docs/GUIDA.md"
