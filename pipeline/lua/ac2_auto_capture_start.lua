-- ac2_auto_capture_start.lua — AUTOMATICO: aspetta il titolo del gioco, avvia Fighter's Honor (4 scritture, GUIDA §2b) e salva lo stato
-- di INIZIO MISSIONE (registri, RAM 2 MiB, scratchpad, GTE) in /tmp/fh_start_A.bin al primo ingresso di FUN_8002bcdc (aggiornamento unita').
-- Formato = quello di pipeline/mipsvm. Non serve premere nulla: le FMV finiscono da sole. Lo lancia tools/capture_mission_start.sh.
-- Uso a mano: ZS1_LUA_SCRIPT=$HOME/GitHub/AC2Remake/pipeline/lua/ac2_auto_capture_start.lua ./run_emulator.sh "Ace Combat 2 (Europe).bin"  (percorso ASSOLUTO)
local STAGE, PLANE, MODULE_TITLE, WAIT_FRAMES = 32, 0, 2, 120
local ENTRY, OUT = 0x8002bcdc, "/tmp/fh_start_A.bin"
local rd32 = emu.read_u32

local function dump(path)
  local f = io.open(path, "wb")
  local t = {}
  for i = 0, 31 do t[#t + 1] = string.pack("<I4", emu.reg(i)) end
  t[#t + 1] = string.pack("<I4I4I4", emu.pc(), 0, 0)
  f:write(table.concat(t)); t = {}
  local a = 0x80000000
  while a < 0x80200000 do
    for i = 0, 4095 do t[#t + 1] = string.pack("<I4", rd32(a + i * 4)) end
    f:write(table.concat(t)); t = {}; a = a + 16384
  end
  for i = 0, 255 do t[#t + 1] = string.pack("<I4", rd32(0x1f800000 + i * 4)) end
  for i = 0, 31 do t[#t + 1] = string.pack("<i4", emu.gte_data(i)) end
  for i = 0, 31 do t[#t + 1] = string.pack("<I4", 0) end
  f:write(table.concat(t)); f:close()
end

local armed, saved = false, false
emu.on_break(function(reason)
  if armed and not saved and emu.pc() == ENTRY then
    dump(OUT); saved = true; emu.remove_breakpoint(ENTRY)
    emu.log("[AUTO] stato di inizio missione salvato in " .. OUT)
  end
  emu.resume()
end)

local stable, frame = 0, 0
emu.on_event(function(ev)
  frame = frame + 1
  if armed then return end
  -- stato globale valido = firma "ACEC" + overlay in RAM; titolo = modulo 2, stabile ~2 s
  local ready = rd32(0x80010000) == 0x43454341 and rd32(0x80018000) == 0x544e4f43
  if ready and rd32(0x800b8184) == MODULE_TITLE then stable = stable + 1 else stable = 0 end
  if stable >= WAIT_FRAMES then
    armed = true
    emu.add_breakpoint(ENTRY)
    emu.write_u32(0x80010030, STAGE); emu.write_u32(0x80010034, PLANE)
    emu.write_u32(0x800b83fc, 4); emu.write_u32(0x800b892c, 1)
    emu.log(string.format("[AUTO] titolo raggiunto al frame %d: Fighter's Honor richiesto, cattura armata", frame))
  end
end, "vblank")
emu.log("[AUTO] in attesa del titolo")
