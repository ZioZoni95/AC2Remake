# Contesto e passaggio di consegne

Fotografia del **2026-11-15** (fine giornata, cambio di PC). Serve a riprendere il lavoro da un altro PC senza la cronologia delle
conversazioni (che non viaggia col repo). Se qualcosa qui contraddice `SCOPERTE.md`, vale `SCOPERTE.md`.

## Obiettivo
Rifare in **Godot 4** la missione **Fighter's Honor** (stadio 32, l'ultima) di Ace Combat 2 (PAL, `SCES-00699`), per uso personale:
**comportamento originale** (si esegue il codice del gioco, non una riscrittura) e **grafica rimasterizzata** (texture 4×, normali,
suddivisione, terreno ridisegnato). Unity solo come confronto opzionale (D3, D13). Asset e marchi sono di Namco/Sony: nulla di estratto
dal disco entra in git.

## Ordine di lavoro deciso dall'utente (2026-11-15)
1. **Logica di missione originale**, letta dal codice con Ghidra e dal VM che lo esegue (in corso)
2. Palette del terreno come le schiarisce il gioco (ora più scure)
3. Cielo e nuvole
4. Musica (traccia trovata; manca la logica a sezioni nella demo)
5. Comandi (joypad) per ultimi

## Stato per fase
| Fase | Stato |
|---|---|
| 0–1 Fondamenta, mappa disco/archivio | ✅ |
| 2 Asset | ✅ estrazione grezza **completa** (`ac2_extract.py all`: 226 entry, 95 MB, 10.654 sotto-file); aerei, TIM, terreno, audio XA ✅; ⚠️ 75 % dei byte ancora **non classificati** (SCOPERTE #37) |
| 3 Reverse missione | ▶️ tabelle T1–T9 ✅; stati e vittoria ✅ (#36); musica ✅ (#38, #39); T7/T8/T3 da completare |
| 4 Slice Godot | ▶️ demo di volo (`flight_demo`, logica semplificata mia) + vista con codice originale (`live_view -- --vm`); manca: logica originale dentro la demo |
| 5 Unity | ⬜ opzionale |

## Fatto e verificato (✅ = provato sul disco reale)
- **Fighter's Honor si avvia** dal titolo scrivendo `[0x80010030]=32`, `[0x80010034]=0`, `[0x800b83fc]=4`, `[0x800b892c]=1` (GUIDA §2b).
- **Interprete MIPS** (`pipeline/mipsvm/`, C): esegue il codice originale con 0 byte di differenza (#31). Ora anche **in servizio**
  (`mipsvm --serve STATO [EXPORT]`: una riga `F TASTI` = un fotogramma originale, pad + `FUN_8002a1f4`; `S file` salva lo stato completo)
  a ~11 ms/fotogramma con `gcc -O3` (con `-march=native` è più lento: non usarlo) (#35).
- **Stato di inizio missione**: `out/fh_start.bin` (catturato dall'emulatore al primo fotogramma). 3000 fotogrammi senza errori.
  **Non si rigenera con la pipeline**: va ricatturato (sotto) oppure copiato dall'altro PC.
- **Joypad** nel codice originale (#34): buffer a `0x800b9040`; si chiama `FUN_8005f6a4` poi il fotogramma. Provato, non ancora collegato a Godot.
- **Stati di missione** (#36): `_DAT_800b867c` 2 intro, 1 in gioco, 4 vittoria, 8 giocatore morto, 0x10 fallimento, 0x40/0x100 pausa/fine.
  Vittoria = nessuna unità attiva con flag `0x800`.
- **Musica** (#38, #39): "Dystopia" = **`traccia_13_ch0.wav`** (voce 13 di `ACE2.STH`; confermata dall'utente all'ascolto). Playlist dello stadio `0x21`:
  `[13, 3, 30, 31, 22, 30, 31, 25, 26]`. La 13 va in **ciclo** finché non muoiono gli **8 bersagli a terra** (slot 12–19); allora parte la
  traccia 3 in ciclo (azione 11 dello script, gruppo T9[4] alla morte dell'unità 35, provato nel VM).
- **Caricamento da zero** (`mipsvm --boot out/iso/SCES_006.99 N`, #35): il loader gira 50 M istruzioni, ma **non carica ancora la missione**
  (hook già fatti: `syscall`, root counter, VSync `0x801dc3b4`; mancano CD `FUN_801d9458/801dbd60/801dbe40`, lettura dei settori dal disco).
- **Ghidra**: progetto `out/ghidra` (loader `main_exe.bin` @`0x801c8000`, overlay 0 `overlay0.bin` @`0x80018000`) e `out/ghidra_ov1`
  (overlay 1 @`0x80160000`, entry `0x80160cc4`, **non ancora studiato**). Il codice di gioco è quasi tutto nell'**overlay 0**.
  Nella GUI (`~/Tools/ghidra/ghidraRun`) gli indirizzi sono quelli del gioco: `G` + `80047470`.

## Cosa NON è in git e va portato o ricostruito sul PC nuovo
| Cosa | Come |
|---|---|
| Disco `Ace Combat 2 (Europe).bin`, BIOS `SCPH-7502.BIN` | **copiare a mano** (`ZonistationOne/games/`, `ZonistationOne/roms/`) |
| `out/` (estratti) | rigenerare, vedi "Ricostruire `out/`" |
| **`out/fh_start.bin`** (2 MB) | si rigenera da solo: `./tools/capture_mission_start.sh` (✅ ~41 s, automatico; RECUPERO_ASSET §9) |
| `out/codice_leggibile/` | si rigenera: `pipeline/ghidra_pick.py` + riscrittura guidata da SCOPERTE #38/#39 (RECUPERO_ASSET §11); derivato dal codice di Namco, mai in git |
| Progetti Ghidra (`out/ghidra`, `out/ghidra_ov1`) | si rifanno con GUIDA §4 (loader e overlay 0) e con il comando sotto (overlay 1); i nomi che l'utente ha dato a mano nella GUI **non** si ritrovano: esportare/copiare la cartella del progetto se servono |
| `engines/godot/assets/` | `./tools/sync_godot_assets.sh` (ora copia anche le tracce 13, 22, 25, 26, 30, 31) |
| Savestate emulatore | **in git** (`savestati/`, eccezione voluta dall'utente), RECUPERO_ASSET §12 |
| Memoria di Claude (`~/.claude/projects/…/memory/`) | copia in `docs/memoria_claude/` (in git): ripristino in `RECUPERO_ASSET.md` §10 |
| Software (Godot 4.7.2, Ghidra 12.2 + JDK 21/25, binutils MIPS, Unity, Real-ESRGAN) | `docs/STRUMENTI.md`; Real-ESRGAN lo lancia l'utente (`bash tools/install_upscaler.sh`, il permesso blocca l'esecuzione automatica) |

## Ricostruire `out/`
Tutti i comandi, con i numeri attesi a ogni passo, stanno in **`docs/RECUPERO_ASSET.md`** (estrazione, audio, Godot, interprete MIPS, Ghidra,
ricattura dello stato di inizio missione, memoria di Claude). Provati da zero il 2026-11-15 in una cartella temporanea: estrazione, audio, Ghidra overlay 0
(⚠️ non provati: installazione strumenti, `sync_godot_assets.sh` da vuoto, ricattura).

## Comandi per vedere lo stato attuale
```sh
godot --path engines/godot res://scenes/flight_demo.tscn                  # demo (logica semplificata, musica = traccia 13)
godot --path engines/godot res://scenes/live_view.tscn -- --vm            # codice ORIGINALE nell'interprete (da out/fh_start.bin), senza comandi
pipeline/mipsvm/mipsvm --serve out/fh_start.bin /tmp/ac2_state.bin        # il servizio da solo (stdin: "F 0", "S file", "Q")
python3 -I pipeline/ac2_vm_frames.py out/fh_start.bin 40 0x80             # N fotogrammi con tasti iniettati
```
Una sola finestra Godot alla volta (più finestre fanno crollare gli FPS). L'emulatore si avvia **sempre col disco**; per le sonde Lua
usare il **percorso assoluto** dello script (`run_emulator.sh` fa `cd` nella cartella dell'emulatore: un percorso relativo non carica nulla).

## Prossimi passi (in ordine)
1. **Demo con la musica originale**: Dystopia (13) in ciclo, passaggio alla 3 quando muoiono gli 8 bersagli; poi i jingle di fine missione.
2. **Logica di missione originale nella demo**: leggere dal VM bersagli rimasti, stato missione, unità distrutte e usarli al posto della mia logica.
3. Caricamento **senza snapshot**: finire gli hook CD di `--boot` per far caricare la missione al loader.
4. Palette del terreno, poi cielo e nuvole, poi comandi (joypad nel VM + tasti Godot).
5. Dati ancora ignoti (#37): testi radio/briefing, effetti sonori (nessun VAB trovato nel DAT), video `STP` canale 8, altri 32 stadi, overlay 1.

## Domande aperte
- Perché l'azione T9[0] indica `arg4 = 36` mentre scendono i PF dello slot 35.
- Cosa suonano e quando i jingle di fine missione (voci 2–8 della playlist); come si ripete la traccia 3.
- Cosa contiene l'overlay 1 (entry 1 del DAT).
- T7 (manovre), T8 (campi di rotta), T3 (ruolo); orientamento di z e allineamento unità/terreno.

## Regole che valgono sempre (le ha date l'utente)
Italiano e risposte brevi (usa il modo "caveman" per risparmiare token); commit e push **solo** su richiesta; **mai** `Co-Authored-By` né
"Generated with"; prima di ogni push `git ls-files` senza asset; emulatore sempre col disco; `ZonistationOne` in sola lettura (branch dedicato,
merge dell'utente); non usare `pkill -f` con il nome dell'emulatore (usare il PID); comandi alle sonde Lua in file temporaneo + `mv`.

Uso di Godot: `docs/GODOT.md`. Strumenti: `docs/STRUMENTI.md`. Lavoro su più PC: `docs/MULTI_PC.md`.

## Errori già fatti (da non ripetere)
- Avviare l'emulatore senza `--game`; percorso relativo dello script Lua (non si carica, nessun errore visibile).
- `lui 0x800c` + addendo **negativo** = `0x800b…`, non `0x800c…` (mi ha fatto cercare i buffer del joypad all'indirizzo sbagliato).
- Disassemblare `SCES_006.99` con base `0x801c8000`: l'intestazione di 0x800 byte sposta tutto; la base giusta per il file intero è `0x801c7800`.
- Scansione ricorsiva dei TIM senza validare la lunghezza; header del modello letto come 16 B (sono 8); decoder TIM 4bpp con `c//4`.
- Ipotizzare il segno del rollio in Godot senza verificarlo a schermo; dare per buono che "azione 11 = dissolvenza" (era il cambio musica).
