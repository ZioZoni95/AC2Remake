# Recuperare gli asset su un altro PC (guida per l'utente e per Claude)

Nulla di estratto dal disco sta in git. Su un PC nuovo, dopo `git clone`, `out/` e `engines/godot/assets/` sono vuoti e vanno
**ricostruiti dal disco originale**. Questa guida dice come, in ordine, con **cosa deve uscire a ogni passo** per capire se è andata bene.
Stato del lavoro e prossimi passi: `docs/CONTESTO.md`. Regole: `CLAUDE.md`.

> **Verifica del 2026-11-15** (rifatta da zero in una cartella temporanea, senza toccare `out/`): ✅ passi 3, 4 (tracce audio), 8 (Ghidra overlay 0) con i numeri attesi
> qui sotto. ⚠️ **Non provati su una macchina pulita**: installazione degli strumenti (passo 1, `bootstrap.sh`), `sync_godot_assets.sh` da `out/` vuoto, la
> ricattura di `fh_start.bin` (passo 9, fatta una volta sola), le sonde Lua.

## Messaggio da incollare al Claude del PC nuovo

> Leggi `CLAUDE.md`, poi `docs/CONTESTO.md` e `docs/RECUPERO_ASSET.md`. Stiamo rifacendo in Godot la missione Fighter's Honor di Ace Combat 2.
> Ricostruisci `out/` seguendo `RECUPERO_ASSET.md` e dimmi per ogni passo se il risultato coincide con i numeri attesi. Non committare e non
> fare push se non te lo chiedo, mai righe `Co-Authored-By`. Lavora in italiano, risposte brevi. Software di terze parti da scaricare
> (Real-ESRGAN): preparali ma li lancio io.

## 0. Cosa deve fare l'utente a mano (Claude non può)

Disco e BIOS sono già sull'altro PC dell'utente: vanno solo **messi al posto giusto** (copiati dal PC vecchio o da dove li ha).

| Cosa | Dove metterla |
|---|---|
| Disco `Ace Combat 2 (Europe).bin` (e `.cue`) | `~/GitHub/ZonistationOne/games/` |
| BIOS PAL `SCPH-7502.BIN` | `~/GitHub/ZonistationOne/roms/` |
| Installare i programmi che Claude non può scaricare/eseguire (Real-ESRGAN: `bash tools/install_upscaler.sh`) | — |

**Tutto il resto Claude lo ricrea da solo** (non serve copiare altro dal PC vecchio):
- `out/fh_start.bin` → `./tools/capture_mission_start.sh` (passo 9, ✅ provato: ~41 s, automatico);
- `out/codice_leggibile/` → passo 11 (script + riscrittura guidata);
- savestate dell'emulatore → sono **già nel repo** in `savestati/` (passo 12);
- progetti Ghidra → passo 8 (i nomi dati a mano nella GUI, se ce ne sono, non si ritrovano: copiare le cartelle `out/ghidra*` solo in quel caso).

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
python3 -I pipeline/ac2_export_godot.py out/fighters_honor/parte2_tabelle.json out/fighters_honor/mission.json   # mission.json (unità T1) per Godot
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144   # 108983 poligoni (104400 + 4583 gonne), 137888 vertici, 25 texture, ~4 s
```
`ac2_mission.py extract` scrive `parte2_tabelle.json` (tabelle T1–T9, SCOPERTE #24–#29) e `manifest.json`; **`mission.json` lo scrive `ac2_export_godot.py`**.

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

## 8. Ghidra (codice del gioco) ✅ provato da zero il 2026-11-15
Il codice di gioco è quasi tutto nell'**overlay 0**; il loader (`SCES_006.99`) ha la libreria CD. Tutto da `~/GitHub/AC2Remake`:
```sh
python3 -I -c "r=open('out/iso/ACE2.DAT','rb').read(2048+657408); open('out/overlay0.bin','wb').write(r[2048+0x800:])"   # overlay 0, base 0x80018000
python3 -I -c "x=open('out/iso/SCES_006.99','rb').read(); open('out/main_exe.bin','wb').write(x[0x800:])"                 # loader, base 0x801c8000
G=~/Tools/ghidra/support/analyzeHeadless; mkdir -p out/ghidra out/codice
$G out/ghidra AC2 -import out/overlay0.bin -overwrite -processor 'MIPS:LE:32:default' -cspec default -loader BinaryLoader -loader-baseAddr 0x80018000   # ~46 s
$G out/ghidra AC2 -import out/main_exe.bin -overwrite -processor 'MIPS:LE:32:default' -cspec default -loader BinaryLoader -loader-baseAddr 0x801c8000
$G out/ghidra AC2 -process overlay0.bin -scriptPath pipeline/ghidra -preScript SetGp.java 800b74f8       # registro gp del gioco
$G out/ghidra AC2 -process main_exe.bin -scriptPath pipeline/ghidra -preScript SetGp.java 801e0108
$G out/ghidra AC2 -process overlay0.bin -noanalysis -scriptPath pipeline/ghidra -postScript ExportAll.java out/codice/overlay0   # atteso: 1217 funzioni, 0 fallite, ~30 s
$G out/ghidra AC2 -process main_exe.bin -noanalysis -scriptPath pipeline/ghidra -postScript ExportAll.java out/codice/loader     # atteso: 316 funzioni
python3 -I pipeline/ghidra_split_mission.py out/codice    # missione_completa.c: attese 513 funzioni, 327768 byte
```
Prova da zero (cartella temporanea): `overlay0.bin` e `main_exe.bin` identici agli originali; export dell'overlay 0 = 1.217 funzioni, 0 fallite; stesse 513 funzioni
della missione. Differenza trascurabile: la dimensione di una funzione fuori dalla missione (`FUN_80073f60`) può variare tra due analisi. Il loader non è stato
reimportato nella prova (solo il file è identico). `out/codice/modulo_gioco.c` (funzioni del modulo di gioco, non della missione) **non ha uno script**: non serve per ora.

Overlay 1 (ACE2.DAT entry 1, **non ancora studiato**), in un progetto separato:
```sh
python3 -I -c "d=open('out/iso/ACE2.DAT','rb'); d.seek(659456+0x800); open('out/overlay1.bin','wb').write(d.read(0x23000))"
mkdir -p out/ghidra_ov1
$G out/ghidra_ov1 OV1 -import out/overlay1.bin -overwrite -processor 'MIPS:LE:32:default' -cspec default -loader BinaryLoader -loader-baseAddr 0x80160000
$G out/ghidra_ov1 OV1 -process overlay1.bin -noanalysis -scriptPath pipeline/ghidra -postScript ExportAll.java out/codice/overlay1   # 276 funzioni
```
Il C decompilato finisce in `out/codice/*.c` (non versionato). Con la GUI aperta sul progetto, `analyzeHeadless` sullo stesso progetto fallisce
(blocco in scrittura): usare un progetto separato o chiudere la GUI. Nella GUI gli indirizzi sono quelli del gioco: `G` e `80047470`.

## 9. Stato di inizio missione `out/fh_start.bin` (automatico) ✅ provato il 2026-11-15
```sh
./tools/capture_mission_start.sh        # richiede emulatore compilato, BIOS e disco al loro posto; ~41 s
python3 -I pipeline/ac2_vm_frames.py out/fh_start.bin 11 0     # controllo: giocatore a z ≈ -149904 che cresce di ~96 a fotogramma
```
Cosa fa: lancia l'emulatore **col disco** con `pipeline/lua/ac2_auto_capture_start.lua` (percorso assoluto: la Lua si carica dalla cartella dell'emulatore),
che aspetta il titolo (le FMV finiscono da sole, non serve premere nulla), scrive le 4 variabili di avvio e salva lo stato al primo
ingresso di `FUN_8002bcdc`. Poi chiude l'emulatore col suo PID e sposta il file. Si apre una finestra dell'emulatore per ~1 minuto: non toccarla.
Attesi: file di **2.098.572 byte**; `pc = 0x8002bcdc`, modulo 4, stadio 32, aereo 0, stato missione 2. Due catture differiscono per poche centinaia di
parole (contatori di tempo): è normale. Se fallisce: `/tmp/capture_mission_start.log`. Non usare `pkill -f` con il nome dell'emulatore.
Alternativa manuale (ROOT MENU e sonda remota): `pipeline/lua/ac2_capture_mission_start.lua`, GUIDA §2b.

## 10. Memoria di Claude (opzionale ma utile)
In `docs/memoria_claude/` ci sono le note che Claude aveva salvato sul progetto (stile di lavoro, regole, stato). Non sono né asset né dati personali
(repo privato). Sul PC nuovo, dopo aver aperto una prima volta Claude Code nella cartella del progetto, copiarle nella sua cartella di memoria:
```sh
M=$(ls -d ~/.claude/projects/*AC2Remake*/ | head -1)memory; mkdir -p "$M" && cp docs/memoria_claude/*.md "$M"/
```
La cartella `~/.claude/projects/<percorso-con-trattini>/` esiste solo dopo la prima sessione in `~/GitHub/AC2Remake`. Anche senza, tutto ciò che serve sta in `CLAUDE.md` e `docs/`.

## 11. C leggibile `out/codice_leggibile/` (rigenerabile, derivato dal codice di Namco: mai in git)
```sh
python3 -I pipeline/ghidra_pick.py            # C grezzo delle 11 funzioni della musica -> out/codice_leggibile/musica_fighters_honor_grezzo.c
python3 -I pipeline/ac2_music_playlist.py     # playlist dello stadio 0x21 dai dati: attesa [13, 3, 30, 31, 22, 30, 31, 25, 26], 72,7 s in totale
```
Poi Claude **riscrive a mano** `out/codice_leggibile/musica_fighters_honor.c` dal testo grezzo, con nomi nostri e commenti, seguendo SCOPERTE **#38 e #39**
(che descrivono a parole tutta la catena): sezioni = dati e modi (`MODE_ONCE/LOOP/NEXT/CYCLE`), playlist di Fighter's Honor, avvio musica
(`FUN_80047470`), API musicale (`FUN_80068fdc`), cosa fa la voce quando finisce (`FUN_80069958`), azioni di missione (`FUN_8005e348`, caso 0xb),
distruzione dell'unità (`FUN_800483d4`, campo `+0x96` dal byte `+0x11` del record T1), fine missione (`FUN_800388ec`). Verifica nel VM: con i PF degli 8
bersagli a terra (slot 12–19) a zero, l'indice della playlist (`[0x800b7ef4]`) passa da 0 a 1 dopo ~1750 fotogrammi (`mipsvm --serve`, comando `S file`).

## 12. Savestate dell'emulatore (in git, decisione dell'utente del 2026-11-15, repo privato)
`savestati/slot0.zst`, `slot2.zst`, `slot3.zst` (4,7 MB ciascuno). Sul PC nuovo: `cp savestati/*.zst ~/GitHub/ZonistationOne/run/savestates/` e caricarli
dall'emulatore. Contenuto: **slot0** = titolo nel ROOT MENU di debug (salvato dall'utente), **slot3** = Fighter's Honor appena avviata (salvato dall'utente
dopo il comando di avvio); **slot2** = non verificato. ⚠️ Un savestate dipende dalla versione dell'emulatore (`ZonistationOne` `master` di oggi): se non
si carica, usare il passo 9. Sono dati del gioco: il repo deve restare **privato**.

## Se qualcosa non torna
- Numeri diversi dagli attesi → fermarsi e segnalarlo prima di proseguire (il disco potrebbe essere un'altra versione: serve la PAL `SCES-00699`).
- Una sonda Lua non fa nulla → percorso relativo dello script (si deve usare l'assoluto) oppure il gioco non è ancora nel ROOT MENU.
- Godot lento → altre finestre aperte (chiuderle); le texture HD richiedono VRAM.
