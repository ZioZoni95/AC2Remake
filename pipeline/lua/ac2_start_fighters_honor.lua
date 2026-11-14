-- ac2_start_fighters_honor.lua — avvia Fighter's Honor (o un'altra missione) dal titolo, senza giocare.
-- Uso:  ZS1_LUA_SCRIPT=pipeline/lua/ac2_start_fighters_honor.lua ./run_emulator.sh "Ace Combat 2 (Europe).bin"
--       (poi saltare le FMV con START finche' non compare il titolo: lo script scatta da solo)
-- Cosa fa (SCOPERTE #18, la sequenza di scritture e' stata VERIFICATA a mano con il canale remoto):
--   [0x80010030] = stadio   (0 = Gambit ... 32 = FIGHTER'S HONOR; buchi 13/17/19)
--   [0x80010034] = aereo    (0..23, entry DAT 30+id)
--   [0x800b83fc] = 4 e [0x800b892c] = 1   -> richiesta del modulo GAME (4), come la voce GAME del ROOT MENU
-- ATTENZIONE: questo script cosi' com'e' NON e' ancora stato eseguito da solo (ne' senza il ROOT MENU forzato):
-- la condizione "titolo raggiunto" e' dedotta da 8184 == 2 (verificato sul titolo). Se non parte, usare
-- ac2_remote.lua e dare i comandi a mano (docs/GUIDA.md, "Avviare Fighter's Honor").
local STAGE, PLANE = 32, 0
local WAIT_FRAMES = 120        -- il titolo deve restare stabile ~2 secondi prima di agire
local MODULE_TITLE = 2

local stable, done, frame = 0, false, 0
emu.on_event(function(ev)
  frame = frame + 1
  if done then return end
  -- lo stato globale e' valido quando ha la firma "ACEC" (0x43454341) e l'overlay e' in RAM
  local ready = emu.read_u32(0x80010000) == 0x43454341 and emu.read_u32(0x80018000) == 0x544e4f43
  if ready and emu.read_u32(0x800b8184) == MODULE_TITLE then stable = stable + 1 else stable = 0 end
  if stable >= WAIT_FRAMES then
    done = true
    emu.write_u32(0x80010030, STAGE)
    emu.write_u32(0x80010034, PLANE)
    emu.write_u32(0x800b83fc, 4)
    emu.write_u32(0x800b892c, 1)
    emu.log(string.format("[FH] stadio %d aereo %d: modulo GAME richiesto (frame %d)", STAGE, PLANE, frame))
  end
end, "vblank")
emu.log("[FH] ac2_start_fighters_honor: in attesa del titolo")
