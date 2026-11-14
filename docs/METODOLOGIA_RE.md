# Metodologia di reverse-engineering della missione

Obiettivo: capire come Ace Combat 2 **guida una singola missione** — waypoint, spawn nemici,
trigger, eventi, punteggio — in modo da replicarla come *dati* in `mission/`, motore-agnostico.

Principio: **dynamic-first**. Il codice del gioco si legge solo quando l'osservazione del gioco
che gira non basta; Ghidra resta l'ultima spiaggia (EXE MIPS LE, base `0x80010000` da header
PS-X EXE).

## Strumenti

- **ZoniStationOne** (riferimento read-only, binary già compilato):
  debugger con breakpoint/watchpoint, disassembly live, savestate F5/F8, due shell (`` ` ``).
- **Probe Lua** (`ZS1_LUA_SCRIPT=…`): superficie `emu.*` in `src/core/lua_debug.c` —
  `pc`, `reg`, `read_u8/16/32`, **`write_u8/16/32`** (dal commit `c59eb77`, in `master` dell'emulatore: RAM e scratchpad, salta il bus), `add_breakpoint`, `add_read_watch`, `add_write_watch`,
  `on_break`, `on_event`, `pause`/`resume`, `disasm`, `gte_data`, `vram16`, `save_state`/`load_state`.
- **Probe esistenti** in `scripts/` dell'emulatore come modelli di stile (es. `savestate_roundtrip.lua`).
- **Ghidra** (rimandabile): decompilazione statica dell'EXE; objdump MIPS per sbirciate.

## Workflow a fasi

0. **Avvio sempre col disco** — `./run_emulator.sh "Ace Combat 2 (Europe).bin"` (mai solo BIOS). Il gioco parte dal boot: per leggere il caricamento si osservano i log (`ZS1_LOG_STDERR=1`, `logs/CDROM.log`) e `emu.cd_state()` (`current_lba`, `drive_state`), senza savestate di forzatura (D10).
1. **Mappatura disco** — `psxcd.list_all` → `ACE2.DAT/STH/STP` + EXE (il modulo non ha CLI).
2. **Mappatura archivio** — `ace2arc list`: le entry DAT sono container annidati (`[N][offset…]`),
   non file singoli; TIM e modelli stanno a livello 1–2 (SCOPERTE #3, #4, #8). Le tabelle missione
   sono presumibilmente blob senza magic: testi di briefing in chiaro nelle entry 7 e 12 (#10).
   Corrispondenza LBA ↔ entry DAT: `lba = 74 + offset_entry/2048` (DAT parte a LBA 74).
3. **Raggiungere la missione con tracciamento** — osservare il caricamento (log CD ↔ entry DAT),
   trovare la variabile stadio/flag di sblocco e forzarla con `emu.write_*` (D8, D10); il savestate
   F5 serve solo come comodità dopo aver raggiunto la missione;
   watchpoint su letture del DAT in RAM (`add_read_watch`) per vedere quali entry/offset
   tocca il loader; log delle letture ↔ indici archivio.
4. **Identificazione strutture** — con gli offset noti si dumpa la RAM (probe Lua) e si
   riconoscono: array di waypoint (coordinate s16/fixed?), record spawn (id modello, pos,
   loadout, AI flags), trigger (condizione → azione).
5. **Validazione incrociata** — gli offset trovati in RAM devono combaciare con
   offset/entry dell'archivio; se combaci, si scrive il decoder dedicato in `pipeline/`.
6. **Estrazione missione → `mission/mission.json`** — formato dati neutro:
   ```json
   { "name": "...", "area": "...", "spawn": [...], "waypoints": [...],
     "triggers": [{"when": "...", "do": [...]}], "rewards": "..." }
   ```
7. **Confronto visivo** — `ZS1_DUMP_FRAME` / screenshot dell'emulatore vs rendimento Godot.

## Regole

- Ogni scoperta va scritta **subito** in `docs/SCOPERTE.md` (offset, test che la prova,
  prossimo passo). Niente conoscenza solo in testa o in chat.
- I probe Lua scritti per AC2 vivono in `pipeline/lua/` (sono strumenti del remake, non
  modifiche all'emulatore).
- Mai fidarsi di un formato "dedotto a occhio": un formato entra in PIPELINE.md solo dopo
  la validazione incrociata del punto 5.
