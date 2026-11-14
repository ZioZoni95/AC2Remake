-- ac2_capture_call.lua — cattura lo stato (registri, RAM 2 MiB, scratchpad, GTE) all'INGRESSO e all'USCITA di una funzione, per
-- confrontarlo con l'interprete pipeline/mipsvm. Si invia come comando di ac2_remote.lua (file temporaneo + mv).
-- Cambia ENTRY e il prefisso dei file. Formato: [regs x32][pc][hi=0][lo=0][RAM][scratchpad 1 KiB][gte data x32][gte control x32 = 0].
local ENTRY = 0x8002bcdc          -- es. 0x8002bcdc aggiornamento unita', 0x8002a1f4 intero fotogramma
local PREFIX = "/tmp/ac2_cap"
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
    dump(PREFIX .. "_A.bin"); ra_addr = emu.reg(31); stage = 1
    emu.remove_breakpoint(ENTRY); emu.add_breakpoint(ra_addr)
    emu.log(string.format("[R] cattura A ok, indirizzo di ritorno %08x", ra_addr))
  elseif stage == 1 and emu.pc() == ra_addr then
    dump(PREFIX .. "_B.bin"); stage = 2; emu.remove_breakpoint(ra_addr)
    emu.log("[R] cattura B ok")
  end
  emu.resume()
end)
emu.log("[R] cattura armata")
