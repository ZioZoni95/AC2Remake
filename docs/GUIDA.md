# Guida all'utilizzo — AC2Remake

Come si usa, in pratica, tutto ciò che c'è nel progetto. Ogni comando segnato ✅ è stato eseguito
sul disco reale; quelli segnati ⚠️ non sono ancora stati provati (lo dice la nota accanto).

Percorsi usati nella guida:

| Nome | Percorso |
|---|---|
| Progetto | `~/GitHub/AC2Remake` |
| Emulatore | `~/GitHub/ZonistationOne` (`master`, da `c59eb77` con `emu.write_*`) |
| Disco | `~/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin` |
| Output estratti | `AC2Remake/out/` (**mai versionati**, vedi regole in README) |

---

## 1. Installazione degli strumenti

| Cosa | Comando | Stato |
|---|---|---|
| Python 3 (solo stdlib) | già presente | ✅ |
| Java 21+25, Ghidra, binutils MIPS (`mipsel-linux-gnu-objdump`) | `./tools/install_re_tools.sh` (chiede `sudo`) | ✅ Ghidra 12.2 + JDK 25 installati e usati in headless |
| Godot 4 (ultima stabile, checksum verificato) | `./tools/install_godot.sh` (senza `sudo`) | ✅ 4.7.2 installato (comando `godot`); non ancora usato per aprire un modello |
| Unity Hub (repo apt ufficiale) | `./tools/install_unity_hub.sh` (chiede `sudo`) | ✅ Hub 4.0.0 installato; l'Editor è in installazione (non verificato che sia finita); Ubuntu 26.04 non è nell'elenco ufficiale di Unity |

Dopo Unity Hub: `unityhub` → *Installs → Install Editor* → Unity 6 LTS (serve probabilmente un
account Unity per la licenza Personal: non verificato).

Godot è l'obiettivo principale; Unity serve come confronto (decisione D3). Entrambi leggono gli
stessi glTF e lo stesso `mission/mission.json`.

---

## 2. Avviare l'emulatore (sempre col disco)

```sh
cd ~/GitHub/AC2Remake
./run_emulator.sh "Ace Combat 2 (Europe).bin"        # ✅ BIOS PAL + disco montato
```

Regola: **mai solo col BIOS**, la prova non direbbe nulla sul gioco. Lo script usa il `.bin` (non
il `.cue`), il BIOS `roms/SCPH-7502.BIN` e forza X11.

Tasti: `Space` = START, `Z` = ×, `C` = ○, `E` = △, `X` = □, `WASD` = croce, `Tab` = SELECT,
`F5`/`F8` = salva/carica savestate, `Esc` = menu rapido, `` ` `` = debugger.

Con una sonda Lua (log su terminale):

```sh
cd ~/GitHub/ZonistationOne/run
ZS1_LUA_SCRIPT=~/GitHub/AC2Remake/pipeline/lua/ac2_stage_probe.lua ZS1_LOG_STDERR=1 \
SDL_VIDEODRIVER=x11 ../ZoniStation_One ../roms/SCPH-7502.BIN \
  --game="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"
```

Funzioni Lua utili (`emu.*`): `read_u8/16/32`, **`write_u8/16/32`** (RAM e scratchpad; solo sul
`master` dal commit `c59eb77`, salta il bus: scrivere dati, non codice), `reg(i)`,
`add_breakpoint`, `add_read_watch`, `add_write_watch`, `on_break`, `on_event(fn,"vblank")`,
`cd_state()` (`current_lba`, `drive_state`), `disasm(addr)`, `save_state/load_state`. Il disco
parte da LBA 74 per `ACE2.DAT`; `ACE2.STP` (streaming/FMV) da 47887.

Le memory card e i log vengono scritti in `ZonistationOne/run/` a ogni avvio.

**Controllo remoto dell'emulatore in esecuzione** (⚠️ ultima versione di `ac2_remote.lua` non rieseguita;
il meccanismo base è ✅): avvia con `ZS1_LUA_SCRIPT=…/pipeline/lua/ac2_remote.lua`, poi scrivi codice Lua in
`/tmp/ac2_cmd.lua`: viene eseguito entro ~0,1 s e cancellato; l'output è nel log (righe `[R]`). Funzioni:
`menu_info()`, `click(i)`, `peek(addr,n)`, `cstr(addr)`, `rd32/rd8/wr32`. Dentro i comandi usa `emu.log(...)`
(la `log` locale della sonda non è visibile). Dettagli e indirizzi: SCOPERTE #12–#14.

---

## 3. Estrarre gli asset dal disco

Tutto in `out/` (non versionato). Bastano tre comandi, nell'ordine:

```sh
cd ~/GitHub/AC2Remake
D="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"

python3 -I pipeline/ac2_extract.py iso    "$D"               out/iso      # ✅ DAT, STH, EXE, SYSTEM.CNF (salta STP)
python3 -I pipeline/ac2_extract.py tims   out/iso/ACE2.DAT   out/tim     # ✅ 2.876 TIM → PNG, 0 errori
python3 -I pipeline/ac2_extract.py models out/iso/ACE2.DAT   out/models  # ✅ 146 modelli → glTF + PNG, ~15 s
```

Risultati: `out/tim/eNNN_...png` (NNN = indice entry del DAT), `out/models/eNNN_S.gltf` più un
`..._pP.png` per ogni palette usata (S = sotto-file, P = indice palette).

Strumenti singoli:

```sh
python3 pipeline/ace2arc.py list DAT out/iso/ACE2.DAT        # ✅ 226 entry (directory dell'archivio)
python3 pipeline/ace2arc.py list STH out/iso/ACE2.STH        # ✅ 68 entry di streaming (offset STH da verificare, SCOPERTE #5)
python3 pipeline/tim2png.py FILE.tim out.png                  # TIM singolo
python3 pipeline/acemodel.py out/iso/ACE2.DAT 179 1 out.obj   # ✅ un solo modello → OBJ (senza texture)
python3 pipeline/tests/test_pipeline.py                       # ✅ 18/18
```

Audio (XA → WAV, `xa_audio.py`): testato solo su fixture sintetica, **non ancora sul disco reale**.

Per aprire un modello: in Godot importa il `.gltf` (le PNG devono stare accanto); le texture hanno
trasparenza (colore 0x0000) e campionamento "nearest" è consigliato.

---

## 4. Leggere il codice del gioco (disassemblaggio)

Il gioco ha due binari, entrambi estratti dal disco:

| Binario | File | Base RAM | Ruolo |
|---|---|---|---|
| Loader | `out/iso/SCES_006.99` (corpo dopo i primi `0x800` B) | `0x801c8000` | carica il resto, salvataggio su card |
| Overlay del gioco | entry 0 di `ACE2.DAT` (corpo dopo i primi `0x800` B) | `0x80018000` | menu, missioni, menu di debug |

Disassemblaggio con binutils (installato, ✅):

```sh
# overlay: estrai il corpo e disassembla
python3 -I -c "r=open('out/iso/ACE2.DAT','rb').read(2048+657408); open('out/overlay0.bin','wb').write(r[2048+0x800:])"
mipsel-linux-gnu-objdump -D -b binary -m mips:3000 -EL --adjust-vma=0x80018000 out/overlay0.bin > out/overlay0.dis
```

Alternativa senza installare nulla: `python3 pipeline/mipsdis.py FILE BASE [OFFSET [N]]` (mini
disassemblatore Python, solo istruzioni comuni; le GTE appaiono come `.word`).

**Ghidra** (✅ headless, versione 12.2). Il plugin PSX non serve per questi blob grezzi. Il codice del gioco
usa molte variabili relative a `gp` ma l'header ha `gp=0`: va impostato (overlay `0x800b74f8`, loader
`0x801e0108`, trovati nel codice di avvio) prima dell'analisi, con `SetGp.java`.

```sh
python3 -I -c "x=open('out/iso/SCES_006.99','rb').read(); open('out/main_exe.bin','wb').write(x[0x800:])"   # loader
G=~/Tools/ghidra/support/analyzeHeadless; mkdir -p out/ghidra
$G out/ghidra AC2 -import out/overlay0.bin -overwrite -processor 'MIPS:LE:32:default' -cspec default -loader BinaryLoader -loader-baseAddr 0x80018000
$G out/ghidra AC2 -import out/main_exe.bin -overwrite -processor 'MIPS:LE:32:default' -cspec default -loader BinaryLoader -loader-baseAddr 0x801c8000
# gp + analisi (una volta per binario)
$G out/ghidra AC2 -process overlay0.bin -scriptPath pipeline/ghidra -preScript SetGp.java 800b74f8
$G out/ghidra AC2 -process main_exe.bin -scriptPath pipeline/ghidra -preScript SetGp.java 801e0108
# domande al progetto (i risultati escono nel log, righe "DecompileAt.java>" / "RefsTo.java>")
$G out/ghidra AC2 -process overlay0.bin -noanalysis -scriptPath pipeline/ghidra -postScript DecompileAt.java 80066858
$G out/ghidra AC2 -process overlay0.bin -noanalysis -scriptPath pipeline/ghidra -postScript RefsTo.java 800b8a60
```
Script in `pipeline/ghidra/`: `SetGp.java`, `DecompileAt.java` (decompila la funzione che contiene l'indirizzo e
ne elenca i chiamanti), `RefsTo.java` (chi legge/scrive un indirizzo). L'analisi di ciascun binario richiede
meno di un minuto.

Dove guardare (già scoperto, vedi `docs/SCOPERTE.md`):
- tabella titoli missioni: array di puntatori a `0x800ad8b4…0x800ad930` (Fighter's Honor è l'ultimo);
- menu di debug `ROOT MENU`: gestito da `FUN_80066858` (`0x80066858`), voci a `0x800ad2e8`; **raggiunto e pilotato da Lua** (SCOPERTE #12–#14, vedi §2);
- salvataggio: 860 byte + checksum a somma di byte; blocco vivo a `[0x801de228] + 0x8b4`.

---

## 5. Regole di lavoro

1. Ogni scoperta in `docs/SCOPERTE.md` con prova riproducibile; ogni scelta in `docs/DECISIONI.md`.
2. Nulla di estratto dal disco entra in git (`out/`, `assets/`, `*.bin` sono ignorati).
3. Le modifiche all'emulatore si fanno su un branch dedicato; il merge in `master` lo fa l'utente (D8, D12).
4. Una prova che avvia l'emulatore senza il disco non vale (D11).
5. I commit non portano righe `Co-Authored-By`.

## 6. Cosa manca (a oggi)

- **Avviare davvero Fighter's Honor** dal menu di debug (GAME, modulo 4) con lo stadio giusto: il menu è pilotato
  da Lua ma nessuna missione è ancora partita; capire il significato di modulo 5 / stage 29 (SCOPERTE #14).
- Riverificare `ac2_remote.lua` (ultima versione, click con breakpoint) alla prossima sessione.
- Identificare l'aereo del giocatore e i nemici tra i 146 modelli; verificare la variante `sub3`.
- Audio dal disco reale; `mission/mission.json` (spawn, waypoint, trigger).
- Import in Godot (gate della Fase 2) e, poi, il confronto con Unity.
- Idea non decisa: pannello "AC2" nel debug workspace dell'emulatore (vedi CONTESTO.md).
