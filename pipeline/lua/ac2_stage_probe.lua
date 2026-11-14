-- ac2_stage_probe.lua — Fase 3: come il gioco sceglie/mostra le missioni.
-- Uso: ZS1_LUA_SCRIPT=pipeline/lua/ac2_stage_probe.lua ./run_emulator.sh "Ace Combat 2 (Europe).bin"
-- 1) log degli accessi al disco: LBA -> offset dentro ACE2.DAT (DAT parte a LBA 74), solo quando cambia area
-- 2) breakpoint sulla lbu della lista missioni (0x8006bc70, overlay entry 0): registra v1/s1 e i byte
--    a [0x800b7618]+0xc70 (ipotesi: id stadio per slot, da verificare)
local DAT_LBA = 74
local last_blk, last_log = -1, -1
emu.on_event(function(ev)
  local cd = emu.cd_state()
  if cd.drive_state == 3 then                       -- 3 = read
    local lba = cd.current_lba
    local blk = math.floor((lba - DAT_LBA) / 16)    -- blocchi da 32 KiB
    if blk ~= last_blk and (lba - last_log) > 64 then
      last_blk, last_log = blk, lba
      emu.log(string.format("[CD] lba=%d dat_off=0x%x", lba, (lba - DAT_LBA) * 2048))
    end
  end
end, "vblank")

local hits = 0
local BP = 0x8006bc70
emu.add_breakpoint(BP)
emu.on_break(function(reason)
  if emu.pc() == BP and hits < 21 then
    hits = hits + 1
    local v1, s1 = emu.reg(3), emu.reg(17)
    local base = emu.read_u32(0x800b7618)
    emu.log(string.format("[LIST] #%d v1=0x%08x s1=%d byte=%d  [800b7618]=0x%08x", hits, v1, s1, emu.read_u8(v1 + 0xc70), base))
    if hits == 21 then emu.remove_breakpoint(BP) end
  end
  emu.resume()
end)
emu.log("ac2_stage_probe: pronta")
