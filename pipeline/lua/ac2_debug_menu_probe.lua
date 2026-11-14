-- ac2_debug_menu_probe.lua — prova di attivazione del ROOT MENU di debug (SCOPERTE #12).
-- FUN_80066858 (0x80066858) disegna/gestisce il menu: si apre se [0x800b89b4] < 0 (init = -1) e
-- [0x800b8a60] & 0x400000. Qui si forza quel bit a ogni vblank, SOLO dopo che l'overlay e' in RAM.
-- Uso: ZS1_LUA_SCRIPT=pipeline/lua/ac2_debug_menu_probe.lua ./run_emulator.sh "Ace Combat 2 (Europe).bin"
-- Cambia FORCE in false per solo osservare (log ogni 300 frame, conteggio chiamate alla funzione).
local FORCE = true
local FN, FLAG, SEL, STATE_PTR = 0x80066858, 0x800b8a60, 0x800b89b4, 0x800b8330
local frame, calls, loaded = 0, 0, false

emu.add_breakpoint(FN)
emu.on_break(function(reason)
  if emu.pc() == FN then calls = calls + 1 end
  emu.resume()
end)

emu.on_event(function(ev)
  frame = frame + 1
  if not loaded and emu.read_u32(0x80018000) == 0x544e4f43 and emu.read_u32(0x800b8330) ~= 0 then
    loaded = true
    emu.log(string.format("[DBG] overlay in RAM al frame %d", frame))
  end
  if loaded and FORCE then
    emu.write_u32(FLAG, emu.read_u32(FLAG) | 0x400000)
  end
  if loaded and frame % 300 == 0 then
    local B = emu.read_u32(STATE_PTR)
    local st = B ~= 0 and emu.read_u32(B + 0x214c) or 0
    emu.log(string.format("[DBG] f%d calls(FN)=%d flag=%08x sel=%08x B=%08x B+214c=%08x menu_aperto=%s",
      frame, calls, emu.read_u32(FLAG), emu.read_u32(SEL), B, st, tostring((st & 2) ~= 0)))
  end
end, "vblank")
emu.log("ac2_debug_menu_probe: pronta, FORCE=" .. tostring(FORCE))
