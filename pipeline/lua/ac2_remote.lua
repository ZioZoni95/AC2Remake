-- ac2_remote.lua — controllo remoto dell'emulatore + pilotaggio del menu di debug a cursore di AC2.
-- Ogni vblank controlla CMD_FILE: se esiste lo esegue (Lua) e lo cancella. L'output va in emu.log ([R] ...).
-- Il menu di debug (FUN_80066858) e' a CURSORE: confronta [0x800b8b94] (Y) con le righe e agisce se
-- [0x800b8a60] & 0x200000 (click). 0x400000 lo apre. Qui si forza 0x400000 dopo che l'overlay e' in RAM.
-- Uso: ZS1_LUA_SCRIPT=pipeline/lua/ac2_remote.lua ./run_emulator.sh "Ace Combat 2 (Europe).bin"
local CMD_FILE = "/tmp/ac2_cmd.lua"
local FLAG, CURY, SEL, STATE_PTR, NITEMS, ACTIONS = 0x800b8a60, 0x800b8b94, 0x800b89b4, 0x800b8330, 0x800b83a8, 0x800b90b8
local FORCE_OPEN = true
local frame, loaded = 0, false
CDLOG = true            -- log delle letture dal disco: LBA e offset nel DAT (DAT parte a LBA 74, STP a 47887)
local last_lba = -1000

local function log(fmt, ...) emu.log("[R] " .. string.format(fmt, ...)) end
rd32 = emu.read_u32; rd8 = emu.read_u8
function wr32(a, v) emu.write_u32(a, v) end

function cstr(addr, max)
  local s = {}
  for i = 0, (max or 40) - 1 do
    local c = rd8(addr + i); if c == 0 then break end
    s[#s + 1] = (c >= 32 and c < 127) and string.char(c) or "."
  end
  return table.concat(s)
end

function peek(addr, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02x", rd8(addr + i)) end
  log("%08x: %s", addr, table.concat(t, " "))
end

function menu_info()
  local B = rd32(STATE_PTR); local desc = rd32(B + 0x2184)
  local n = rd32(NITEMS)
  log("B=%08x state=%08x desc=%08x n=%d top=%d h=%d cursorY=%d flag=%08x sel=%08x",
    B, rd32(B + 0x214c), desc, n, rd32(desc + 0xc), rd32(desc + 0x20), rd32(CURY), rd32(FLAG), rd32(SEL))
  for i = 0, math.min(n, 20) - 1 do log("  voce %d: azione=%d", i, rd32(ACTIONS + 4 * i)) end
end

-- click sulla voce i del menu. NON basta scrivere Y+bit di click al vblank: il gioco riscrive ogni frame
-- [0x800b894c] (deve valere 0 perche' il click valga) e la posizione. Quindi si inietta DENTRO un breakpoint
-- su 0x80066ab0 (inizio dei controlli di FUN_80066858). Verificato (SCOPERTE #13): cosi' il click viene accolto.
-- ATTENZIONE: la riga colpita risulta sfasata di +1 rispetto a i (click(5) ha dato azione 10 invece di 7).
local pending, click_y_bp = 0, 0
local BP_CLICK = 0x80066ab0
function click(i)
  local B = rd32(STATE_PTR); local desc = rd32(B + 0x2184)
  click_y_bp = rd32(desc + 0xc) + i * rd32(desc + 0x20) + rd32(desc + 0x20) // 2
  pending = 2
  log("click voce %d (Y=%d)", i, click_y_bp)
end
emu.add_breakpoint(BP_CLICK)
emu.on_break(function(reason)
  if emu.pc() == BP_CLICK and pending > 0 then
    pending = pending - 1
    emu.write_u32(0x800b894c, 0)
    emu.write_u32(CURY, click_y_bp)
    emu.write_u32(FLAG, rd32(FLAG) | 0x200000)
  end
  emu.resume()
end)

-- Avvia direttamente una missione dal titolo (SCOPERTE #18, VERIFICATO con stadio 32 = Fighter's Honor):
-- scrive lo stadio e l'aereo nello stato globale e richiede il modulo GAME (=4), come farebbe la voce GAME.
-- stage 0..32 (0 = Gambit, 32 = Fighter's Honor), plane 0..23. Va chiamata dal titolo, MENU di debug aperto.
function start_stage(stage, plane)
  wr32(0x80010030, stage); wr32(0x80010034, plane or 0)
  wr32(0x800b83fc, 4); wr32(0x800b892c, 1)
  log("start_stage(%d, %d): modulo 4 richiesto", stage, plane or 0)
end

emu.on_event(function(ev)
  frame = frame + 1
  if CDLOG then
    local cd = emu.cd_state()
    if cd.drive_state == 3 then
      local lba = cd.current_lba
      if math.abs(lba - last_lba) > 40 then
        last_lba = lba
        if lba < 47886 then log("[CD] lba=%d DAT off=0x%x", lba, (lba - 74) * 2048)
        else log("[CD] lba=%d STP off=0x%x", lba, (lba - 47887) * 2048) end
      end
    end
  end
  if not loaded and rd32(0x80018000) == 0x544e4f43 and rd32(STATE_PTR) ~= 0 then
    loaded = true; log("overlay in RAM al frame %d", frame)
  end
  if loaded then
    local v = rd32(FLAG)
    if FORCE_OPEN then v = v | 0x400000 end
    v = v & ~0x200000
    emu.write_u32(FLAG, v)
  end
  if frame % 6 == 0 then
    local f = io.open(CMD_FILE, "r")
    if f then
      local src = f:read("a"); f:close(); os.remove(CMD_FILE)
      local fn, err = load(src, "cmd")
      if not fn then log("errore sintassi: %s", tostring(err))
      else
        local ok, e = pcall(fn)
        log("cmd %s%s", ok and "ok" or "ERRORE: ", ok and "" or tostring(e))
      end
    end
  end
end, "vblank")
log("ac2_remote pronta (comandi in %s)", CMD_FILE)
