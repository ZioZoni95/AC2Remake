---
name: feedback-emulator-always-with-game
description: "Avviare sempre ZoniStation_One con il disco di Ace Combat 2 (--game=), mai solo il BIOS"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 36c25cc4-9b6d-4286-919f-11a27efbbb66
  modified: 2026-11-14T14:16:42.875Z
---

Quando lancio l'emulatore (ZonistationOne) per prove, probe Lua o test, devo SEMPRE montare il gioco:
`--game="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"` (il `.bin`, non il `.cue`; BIOS
`roms/SCPH-7502.BIN`; da `run/`; `SDL_VIDEODRIVER=x11`). Lo script `AC2Remake/run_emulator.sh <nome.bin>` lo fa.

**Why:** l'utente mi ha ripreso dopo che ho lanciato l'emulatore col solo BIOS per testare le funzioni Lua
(2026-11-14): senza disco la prova non dice nulla sul remake e fa perdere tempo.

**How to apply:** ogni comando che avvia `ZoniStation_One` deve contenere `--game=` con l'immagine di AC2,
salvo richiesta esplicita contraria. Il branch di lavoro dell'emulatore per le modifiche Lua è
`feature/lua-memory-write` (aggiunge `emu.write_u8/16/32`).
