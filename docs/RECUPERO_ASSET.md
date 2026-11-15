# Recuperare gli asset su un altro PC (guida per l'utente e per Claude)

Nulla di estratto dal disco sta in git. Su un PC nuovo, dopo `git clone`, `out/` e `engines/godot/assets/` sono vuoti e vanno
**ricostruiti dal disco originale**. Questa guida dice come, in ordine, con **cosa deve uscire a ogni passo** per capire se è andata bene.
Stato del lavoro e prossimi passi: `docs/CONTESTO.md`. Regole: `CLAUDE.md`.

> ✅ = provato il 2026-11-15 sulla macchina di origine; ⚠️ = la sequenza completa **non è stata rieseguita da zero** su una macchina pulita.

## Messaggio da incollare al Claude del PC nuovo

> Leggi `CLAUDE.md`, poi `docs/CONTESTO.md` e `docs/RECUPERO_ASSET.md`. Stiamo rifacendo in Godot la missione Fighter's Honor di Ace Combat 2.
> Ricostruisci `out/` seguendo `RECUPERO_ASSET.md` e dimmi per ogni passo se il risultato coincide con i numeri attesi. Non committare e non
> fare push se non te lo chiedo, mai righe `Co-Authored-By`. Lavora in italiano, risposte brevi. Software di terze parti da scaricare
> (Real-ESRGAN): preparali ma li lancio io.

## 0. Cosa deve fare l'utente a mano (Claude non può)

| Cosa | Dove metterla |
|---|---|
| Disco `Ace Combat 2 (Europe).bin` (e `.cue`) | `~/GitHub/ZonistationOne/games/` |
| BIOS PAL `SCPH-7502.BIN` | `~/GitHub/ZonistationOne/roms/` |
| `out/fh_start.bin` (2 MB, stato di inizio missione) dal PC vecchio | `~/GitHub/AC2Remake/out/fh_start.bin` (oppure ricatturarlo: passo 9) |
| `out/codice_leggibile/musica_fighters_honor.c` (scritto a mano, derivato dal codice di Namco, **mai in git**) | `~/GitHub/AC2Remake/out/codice_leggibile/` |
| Cartelle dei progetti Ghidra `out/ghidra` e `out/ghidra_ov1` **solo se** contengono nomi dati a mano nella GUI | stesse posizioni (altrimenti si rifanno, passo 8) |
| Installare i programmi lanciati dall'utente (es. Real-ESRGAN: `bash tools/install_upscaler.sh`) | — |

`ZonistationOne` deve stare su `master` aggiornato (contiene `emu.write_*`) e affiancato ad `AC2Remake`.

## 1. Strumenti da installare (versioni con cui è stato provato; dettagli e fonti in `docs/STRUMENTI.md`)

Macchina di origine: Ubuntu 26.04, GPU NVIDIA GTX 1050 Mobile 4 GB (Vulkan), Python 3.14.4, gcc 15.2.0, OpenJDK 25.

| Strumento | Serve per | Obbligatorio? | Come |
|---|---|---|---|
| `git` + accesso GitHub (SSH) ai repo `ZioZoni95/AC2Remake` (privato) e `ZioZoni95/ZonistationOne` | codice | sì | `sudo apt install git` |
| Python 3 (solo libreria standard, si lancia con `-I`) | tutta la pipeline | sì | già nel sistema |
| `gcc` e `make` | compilare l'interprete MIPS (`pipeline/mipsvm`) e l'emulatore | sì | `sudo apt install build-essential` |
| Emulatore **ZonistationOne** (branch `master`, commit `c59eb77` o successivo, con `emu.write_*`) + SDL3, GLEW | avviare il gioco, catturare lo stato, sonde Lua | sì per ricatturare `fh_start.bin`; no se la si copia | `./tools/bootstrap.sh` (clona e compila ⚠️) o README di ZonistationOne |
| **Godot 4.7.2** stabile (Forward+, Vulkan) | demo e viste | sì | `./tools/install_godot.sh` (senza sudo, verifica SHA-512) → `~/.local/bin/godot` e `~/Tools/godot` |
| **Java** OpenJDK 21 e 25 | Ghidra | per Ghidra | `./tools/install_re_tools.sh` (sudo) |
| **Ghidra 12.2** (build 2026-10-16) | leggere e decompilare il codice del gioco (GUI `ghidraRun` e `analyzeHeadless`) | per il lavoro sul codice | `./tools/install_re_tools.sh` → `~/Tools/ghidra` |
| binutils MIPS (`mipsel-linux-gnu-objdump`) | disassemblare il codice | consigliato | `./tools/install_re_tools.sh` (sudo) |
| **Real-ESRGAN ncnn-vulkan** (build Ubuntu 20220424, v0.2.5.0, ~45 MB) | texture 4× | opzionale | **lo lancia l'utente**: `bash tools/install_upscaler.sh` (Claude non può: il permesso blocca lo scarico ed esecuzione di software di terzi) |
| Unity Hub 4.0.0 + Editor 6000.6.9f1 | solo il confronto opzionale con Unity (fase 5) | no | `./tools/install_unity_hub.sh` (sudo); mai usato |

Ordine consigliato: `git clone` di entrambi i repo affiancati in `~/GitHub/` → `./tools/bootstrap.sh` → `./tools/install_re_tools.sh` →
`./tools/install_godot.sh` → (utente) `bash tools/install_upscaler.sh`. Verifica: `godot --version` (4.7.2…), `gcc --version`,
`java -version`, `ls ~/Tools/ghidra`, `which mipsel-linux-gnu-objdump`. ⚠️ Gli script di installazione non sono stati provati su una macchina pulita.

## 2. Verifica del repo
```sh
cd ~/GitHub/AC2Remake
python3 pipeline/tests/test_pipeline.py        # atteso: 18/18
```

## 3. Estrazione dal disco (tutti i comandi con `python3 -I`)
```sh
DISCO="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"
python3 -I pipeline/ac2_extract.py iso    "$DISCO" out/iso                   # ACE2.DAT 97,9 MB, ACE2.STH, SCES_006.99, SYSTEM.CNF (STP escluso)
python3 -I pipeline/ac2_extract.py all    out/iso/ACE2.DAT out/dat_all       # atteso: 226 entry, 10654 sotto-file, 95370 KB
python3 -I pipeline/ac2_extract.py tims   out/iso/ACE2.DAT out/tim           # atteso: 2876 TIM, 0 errori
python3 -I pipeline/ac2_extract.py models out/iso/ACE2.DAT out/models        # atteso: 146 esportati, 0 saltati
python3 -I pipeline/ac2_aircraft.py all out/aerei                            # 24 aerei con texture
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor             # blocco di Fighter's Honor (11 parti, 49 TIM, 13 unità)
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144   # 104400 poligoni, 25 texture, ~4 s
```
`ac2_mission.py extract` scrive anche `mission.json` e `parte2_tabelle.json`: le tabelle T1–T9 (SCOPERTE #24–#29).

## 4. Audio
```sh
python3 -I pipeline/ac2_audio.py tracks "$DISCO" out/iso/ACE2.STH out/audio   # 64 tracce WAV (112 MB), ~1 min
python3 -I pipeline/ac2_sfx_placeholder.py                                    # 4 effetti segnaposto (sfx_*.wav)
```
**La musica di Fighter's Honor è `out/audio/traccia_13_ch0.wav`** ("Dystopia"). Playlist: `[13, 3, 30, 31, 22, 30, 31, 25, 26]` (SCOPERTE #38/#39).
Il file `ACE2.STP` (407 MB) non va estratto: l'audio lo legge direttamente `ac2_audio.py` dal disco.

## 5. Copia in Godot
```sh
./tools/sync_godot_assets.sh        # copia modelli, terreno, sfx e le tracce 00–06, 13, 22, 25, 26, 30, 31 in engines/godot/assets/
```
Opzionale (modernizzazione, lo lancia l'utente): `bash tools/install_upscaler.sh`, poi `tools/upscale_gltf.py` (docs/GODOT.md).

## 6. Interprete MIPS (il codice originale)
```sh
gcc -O3 -o pipeline/mipsvm/mipsvm pipeline/mipsvm/mipsvm.c pipeline/mipsvm/gte.c pipeline/mipsvm/gte_ops.c   # NON -march=native (più lento)
```

## 7. Prove che tutto funziona
```sh
python3 -I pipeline/ac2_vm_frames.py out/fh_start.bin 11 0x80      # stampa posizione e angoli del giocatore; senza errori
godot --path engines/godot res://scenes/flight_demo.tscn           # demo giocabile, HUD "traccia_13_ch0"
godot --path engines/godot res://scenes/live_view.tscn -- --vm     # codice originale nel VM (senza comandi)
```
Una sola finestra Godot alla volta.

## 8. Ghidra (codice del gioco)
Loader e overlay 0: `docs/GUIDA.md` §4 (progetto `out/ghidra`, programmi `main_exe.bin` @`0x801c8000` e `overlay0.bin` @`0x80018000`;
`out/main_exe.bin`/`out/overlay0.bin` si ricavano da `SCES_006.99` senza i primi 0x800 byte e da `ACE2.DAT` entry 0 dopo l'intestazione).
Overlay 1 (ACE2.DAT entry 1, **non ancora studiato**):
```sh
python3 -I - <<'E'
d=open("out/iso/ACE2.DAT","rb"); d.seek(659456+0x800); open("out/overlay1.bin","wb").write(d.read(0x23000))
E
~/Tools/ghidra/support/analyzeHeadless out/ghidra_ov1 OV1 -import out/overlay1.bin -overwrite -processor 'MIPS:LE:32:default' -cspec default -loader BinaryLoader -loader-baseAddr 0x80160000
~/Tools/ghidra/support/analyzeHeadless out/ghidra_ov1 OV1 -process overlay1.bin -noanalysis -scriptPath pipeline/ghidra -postScript ExportAll.java out/codice/overlay1
```
Il C decompilato finisce in `out/codice/*.c` (non versionato). Con la GUI aperta sul progetto, `analyzeHeadless` sullo stesso progetto fallisce
(blocco in scrittura): usare un progetto separato o chiudere la GUI.

## 9. Ricatturare lo stato di inizio missione (solo se manca `out/fh_start.bin`)
1. Lancia l'emulatore **col disco** e la sonda, con percorso **assoluto**: `ZS1_LUA_SCRIPT=$HOME/GitHub/AC2Remake/pipeline/lua/ac2_remote.lua ./run_emulator.sh "Ace Combat 2 (Europe).bin"`.
2. Salta le FMV con START fino al titolo; dopo ~50–60 s compare il ROOT MENU in alto a sinistra (GUIDA §2b).
3. **Solo allora** manda `pipeline/lua/ac2_capture_mission_start.lua` come comando (file temporaneo + `mv` su `/tmp/ac2_cmd.lua`): arma la cattura e scrive le 4 variabili.
4. Il file `/tmp/fh_start_A.bin` (2.098.572 byte) va copiato in `out/fh_start.bin`. Controllo: `ac2_vm_frames.py out/fh_start.bin 11 0` stampa il giocatore a `(-47100, -7000, -102000)` dopo alcuni fotogrammi.
5. Non usare `pkill -f` con il nome dell'emulatore: usare il PID.

## Se qualcosa non torna
- Numeri diversi dagli attesi → fermarsi e segnalarlo prima di proseguire (il disco potrebbe essere un'altra versione: serve la PAL `SCES-00699`).
- Una sonda Lua non fa nulla → percorso relativo dello script (si deve usare l'assoluto) oppure il gioco non è ancora nel ROOT MENU.
- Godot lento → altre finestre aperte (chiuderle); le texture HD richiedono VRAM.
