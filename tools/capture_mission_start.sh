#!/usr/bin/env bash
# Ricostruisce out/fh_start.bin (stato di inizio missione di Fighter's Honor) lanciando l'emulatore COL DISCO e uno script Lua che
# aspetta il titolo, avvia lo stadio e salva lo stato. Uso: ./tools/capture_mission_start.sh [timeout_secondi, default 300]
# Apre una finestra dell'emulatore per circa 1-3 minuti (le FMV partono da sole; non serve premere nulla). Percorsi ASSOLUTI (la Lua si
# carica dalla cartella dell'emulatore). L'emulatore viene chiuso col suo PID, mai con pkill -f.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"; EMU="$HOME/GitHub/ZonistationOne"; OUT=/tmp/fh_start_A.bin; TMO="${1:-300}"
[[ -x "$EMU/ZoniStation_One" ]] || { echo "manca l'emulatore compilato: $EMU/ZoniStation_One (tools/bootstrap.sh)"; exit 1; }
[[ -f "$EMU/roms/SCPH-7502.BIN" ]] || { echo "manca il BIOS: $EMU/roms/SCPH-7502.BIN"; exit 1; }
[[ -f "$EMU/games/Ace Combat 2 (Europe).bin" ]] || { echo "manca il disco: $EMU/games/Ace Combat 2 (Europe).bin"; exit 1; }
rm -f "$OUT"
( cd "$EMU/run" && ZS1_LUA_SCRIPT="$ROOT/pipeline/lua/ac2_auto_capture_start.lua" SDL_VIDEODRIVER=x11 \
  exec "$EMU/ZoniStation_One" "$EMU/roms/SCPH-7502.BIN" --game="$EMU/games/Ace Combat 2 (Europe).bin" >/tmp/capture_mission_start.log 2>&1 ) &
PID=$!
for ((i = 0; i < TMO; i++)); do
  if [[ -s "$OUT" ]]; then sleep 2; break; fi        # il file e' grande (2 MB): attende che la scrittura finisca
  kill -0 "$PID" 2>/dev/null || { echo "l'emulatore si e' chiuso prima della cattura (log: /tmp/capture_mission_start.log)"; exit 1; }
  sleep 1
done
kill "$PID" 2>/dev/null || true
[[ -s "$OUT" ]] || { echo "timeout: nessuno stato catturato in ${TMO}s (log: /tmp/capture_mission_start.log)"; exit 1; }
SZ=$(stat -c %s "$OUT"); [[ "$SZ" == 2098572 ]] || { echo "dimensione inattesa: $SZ (attesi 2098572)"; exit 1; }
mkdir -p out && mv "$OUT" out/fh_start.bin
echo "ok: out/fh_start.bin ($SZ byte). Prova: python3 -I pipeline/ac2_vm_frames.py out/fh_start.bin 11 0"
