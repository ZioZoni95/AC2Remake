-- ac2_capture_mission_start.lua — cattura lo stato di INIZIO MISSIONE (Fighter's Honor) e avvia lo stadio. Si invia come comando di
-- ac2_remote.lua (file temporaneo + mv) quando il gioco e' nel ROOT MENU del titolo (docs/GUIDA.md §2b). Scrive /tmp/fh_start_A.bin;
-- poi copiarlo in out/fh_start.bin. Dopo averlo catturato puo' servire a pipeline/mipsvm (--serve) e a live_view --vm.
-- Origine: ac2_capture_call.lua — cattura lo stato (registri, RAM 2 MiB, scratchpad, GTE) all'INGRESSO e all'USCITA di una funzione, per
-- confrontarlo con l'interprete pipeline/mipsvm. Si invia come comando di ac2_remote.lua (file temporaneo + mv).
-- Cambia ENTRY e il prefisso dei file. Formato: [regs x32][pc][hi=0][lo=0][RAM][scratchpad 1 KiB][gte data x32][gte control x32 = 0].
local ENTRY = 0x8002bcdc          -- es. 0x8002bcdc aggiornamento unita', 0x8002a1f4 intero fotogramma
local PREFIX = "/tmp/fh_start"
local stage, ra_addr = 0, 0
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
emu.add_breakpoint(ENTRY)
emu.on_break(function(reason)
  if stage == 0 and emu.pc() == ENTRY then
    dump(PREFIX .. "_A.bin"); stage = 2; emu.remove_breakpoint(ENTRY)
    emu.log("[R] stato di inizio missione salvato")
  end
  emu.resume()
end)
wr32(0x80010030, 32); wr32(0x80010034, 0); wr32(0x800b83fc, 4); wr32(0x800b892c, 1)
emu.log("[R] cattura armata + avvio Fighter's Honor")
