# Contesto e passaggio di consegne

Fotografia del 2026-11-14. Serve a riprendere il lavoro da un altro PC senza la cronologia delle
conversazioni (che non viaggia col repo). Se qualcosa qui contraddice `SCOPERTE.md`, vale `SCOPERTE.md`.

## Obiettivo
Rifare in Godot 4 (poi confronto con Unity) la missione **Fighter's Honor** di Ace Combat 2, con asset
estratti dal disco originale per uso personale e dati di missione ricostruiti dal reverse engineering.

## Stato per fase
| Fase | Stato |
|---|---|
| 0–1 Fondamenta, mappa disco/archivio | ✅ |
| 2 Asset | ▶️ TIM (2.876) e modelli (146 glTF texturizzati) estratti; da fare: audio dal disco reale, identificare aereo giocatore/nemici, import in Godot |
| 3 Reverse missione | ▶️ missione scelta; **bloccati** sul come raggiungerla senza completare il gioco |
| 4–6 Slice Godot, Unity, chiusura | ⬜ |

## Stato al 2026-11-14 (fine sessione)
**Fatto e verificato:**
- Fighter's Honor **si avvia dal titolo** scrivendo `[0x80010030]=32`, `[0x80010034]=0`, `[0x800b83fc]=4`,
  `[0x800b892c]=1` (SCOPERTE #18; GUIDA §2b; script `pipeline/lua/ac2_start_fighters_honor.lua`, ⚠️ non ancora
  rieseguito come script autonomo; `start_stage()` in `ac2_remote.lua` idem). Niente savestate di forzatura.
- **Aerei**: i 24 giocabili (nomi, id 0–23, entry `30 + id`) estratti con texture: `ac2_aircraft.py` (SCOPERTE #22).
- **Missione**: blocco dati di Fighter's Honor (entry 166; 165/167 = varianti) estratto: 11 parti grezze, 49 TIM,
  13 unità texturizzate, VRAM ricostruita (`ac2_mission.py`, SCOPERTE #19, #20, #23). Texture TIM = VRAM del gioco al 100%.
- In RAM a missione in corso: tabella tipi unità, pool di 63 oggetti da 372 B, struttura del giocatore (SCOPERTE #20, #21).
- Strumenti: Godot 4.7.2, Unity Hub 4.0.0 + Editor 6000.6.9f1, Ghidra 12.2 (headless) + JDK 25, binutils MIPS.

**Prossimi passi, in ordine:**
1. **Decodificare i campi delle tabelle della parte 2** (già estratta: `parte2_tabelle.json`, SCOPERTE #24–#25; T2 = piazzamento verificato)
   e poi le parti 0, 3, 4 (terreno) e dalle tabelle comuni
   5/7, aiutandosi con la RAM a missione in corso: pool a `[0x800b8748]` (63 slot × 0x174, coordinate a 32 bit con 11 bit
   frazionari alle parole 9–11 dello slot), tipo → modello con la tabella tipi (`[0x800b84fc]`). Confrontare con Gambit
   (entry 79) per separare dati comuni e specifici. Risultato atteso: `mission/mission.json`.
2. **Godot** (avviato; modernizzazione dell'XFA-27 con geometria morbida + texture 4× approvata dall'utente): ✅ visualizzatore dell'XFA-27 in `engines/godot` (PS1 fedele / moderna, GUIDA §2c). Prossimo: aggiungere
   un'unità nemica al visualizzatore (gate Fase 2), poi scena di volo (camera, modello di volo arcade, HUD) e terreno.
3. Audio dal disco reale (XA→WAV) e musica/voci della missione.
4. Valutare aereo preferito (`+0x34`) e avanzamento (`+0x8b4`) per il gioco "completo"; poi il confronto con Unity.

**Idea in sospeso (non decisa):** pannello "AC2" nel debug workspace dell'emulatore (ImGui, su un branch dedicato, merge a
cura dell'utente) per aprire il menu, scegliere lo stadio e mostrare le variabili. Il debug workspace ha già una *Lua
Console* con esecuzione di codice e di file.

**Come riprendere (passi esatti):**
```sh
cd ~/GitHub/ZonistationOne/run
ZS1_LUA_SCRIPT=$HOME/GitHub/AC2Remake/pipeline/lua/ac2_remote.lua ZS1_LOG_STDERR=1 SDL_VIDEODRIVER=x11 \
  ../ZoniStation_One ../roms/SCPH-7502.BIN --game="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin" \
  2>&1 | tee /tmp/remote.log
# nella finestra: Space per saltare le FMV fino al titolo; dopo ~50-60 s compare ROOT MENU in alto a sinistra
# comandi: scrivi in un file TEMPORANEO e poi mv (atomico: se la sonda legge il file mentre lo scrivi lo perde)
echo 'menu_info()' > /tmp/ac2_cmd.tmp && mv /tmp/ac2_cmd.tmp /tmp/ac2_cmd.lua   # risultato nel log, prefisso [R]
```
Attenzioni: se il gioco entra in **modalità demo** sul titolo i valori cambiano (è già successo); non usare
`pkill -f "ZoniStation_One ..."` (uccide anche la shell che lo contiene: usare il PID); `ac2_remote.lua` dopo
l'ultima modifica (click con breakpoint) **non è stato rieseguito**; il savestate dell'utente è locale a quella
macchina (non in git). Il `ROOT MENU` si vede in alto a sinistra con glifi sporchi: è normale.

**Idea in sospeso (non decisa):** un pannello "AC2" nel debug workspace dell'emulatore (ImGui, su un branch
dedicato, merge a cura dell'utente) con pulsanti per aprire il menu, scegliere lo stadio e mostrare le variabili. Il debug
workspace ha già una *Lua Console* con esecuzione di codice e di file. Rimandato a dopo la prima missione avviata.

Uso di Godot: `docs/GODOT.md`. Strumenti e versioni: `docs/STRUMENTI.md`. Lavoro su più PC: `docs/MULTI_PC.md`.

## Ambiente: cosa serve su una macchina nuova
| Cosa | Dove sta | Come si ottiene |
|---|---|---|
| Questo repo | GitHub (privato) `ZioZoni95/AC2Remake` | `git clone` |
| Emulatore | GitHub `ZioZoni95/ZonistationOne`, **`master`** (contiene `emu.write_*` dal commit `c59eb77`) | `git clone` + `make` (dipendenze: README dell'emulatore, SDL3) |
| BIOS PAL `SCPH-7502.BIN` | **non in git** | copiare in `ZonistationOne/roms/` |
| Disco `Ace Combat 2 (Europe).bin` | **non in git** | copiare in `ZonistationOne/games/` (usare il `.bin`) |
| Asset estratti, disassemblati | non in git (`out/`) | rigenerare con `docs/GUIDA.md` §3–4 |
| Java, Ghidra, Godot, Unity Hub | — | `tools/install_re_tools.sh`, `install_godot.sh`, `install_unity_hub.sh` |

Layout atteso (`run_emulator.sh` lo dà per scontato): `~/GitHub/AC2Remake` e `~/GitHub/ZonistationOne`.
Tutto in un comando: `./tools/bootstrap.sh` (clona, compila, controlla cosa manca; ⚠️ non ancora provato su una macchina pulita).

## Verifica rapida che l'ambiente funzioni
```sh
python3 pipeline/tests/test_pipeline.py                              # 18/18
python3 -I pipeline/ac2_extract.py iso "<percorso>/Ace Combat 2 (Europe).bin" out/iso
python3 -I pipeline/ac2_extract.py models out/iso/ACE2.DAT out/models  # attesi: 146 esportati, 0 saltati
./run_emulator.sh "Ace Combat 2 (Europe).bin"                         # parte il gioco
```

## Stato degli strumenti sulla macchina di origine (2026-11-14)
Godot 4.7.2 ✅, Unity Hub 4.0.0 ✅ + Editor 6000.6.9f1 ✅, binutils MIPS ✅, Java 21+25 ✅;
Ghidra 12.2 e JDK 25 ✅; Unity Editor 6000.6.9f1 installato ✅ (mai avviato: su Ubuntu 26.04 non è nell'elenco ufficiale di Unity).

## Errori già fatti (da non ripetere)
- Avviare l'emulatore senza `--game`. 
- Scansione ricorsiva dei TIM senza validare la lunghezza: migliaia di falsi positivi.
- Header del modello letto come 16 B (sono 8) e numero di vertici stimato a occhio.
- Decoder TIM 4bpp con indice pixel `c//4` (era `c//2`); la fixture solo 16bpp non lo vedeva.
- Letto l'header dell'entry 0 dall'inizio del DAT invece che da +2048.
