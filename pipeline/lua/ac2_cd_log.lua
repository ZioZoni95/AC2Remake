-- ac2_cd_log.lua — avvia Fighter's Honor (come ac2_start_fighters_honor.lua) e registra i comandi CD del loader (FUN_801d9458):
-- SetFilter (0x0d) = file+canale XA, Setloc (2), ReadS (0x1b)/Play (3). Serve a trovare la musica della missione (SCOPERTE #35).
dofile((os.getenv("AC2_DIR") or ".") .. "/pipeline/lua/ac2_start_fighters_honor.lua")
local BP = 0x801d9458
emu.add_breakpoint(BP)
emu.on_break(function(reason)
  if emu.pc() == BP then
    local a0, a1 = emu.reg(4), emu.reg(5)
    local p = {}
    for i = 0, 3 do p[#p + 1] = string.format("%02x", emu.read_u8(a1 + i)) end
    emu.log(string.format("[CD] cmd=0x%02x param=%s", a0 & 0xff, table.concat(p, " ")))
  end
  emu.resume()
end)
