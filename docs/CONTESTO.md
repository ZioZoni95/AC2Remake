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

## Il problema aperto (dove ripartire) — stato al 2026-11-14, sessione interrotta
Fighter's Honor è l'ultima missione; Free Mission si sblocca solo finendo il gioco. **Abbiamo trovato il
menu di debug del gioco e lo pilotiamo da Lua** (SCOPERTE #12–#14). Stato esatto:
- Il `ROOT MENU` compare forzando `[0x800b8a60] |= 0x400000` a ogni vblank (dopo che l'overlay è in RAM).
- È a **cursore**: si clicca iniettando Y + `894c=0` + bit `0x200000` dentro un breakpoint a `0x80066ab0`.
- Voci: FONT, TITLE, BRIEFING, GAME (+2 giapponesi). GAME dovrebbe essere azione 7 → modulo 4.
- Ultimo esperimento: un click sfasato di una riga ha dato modulo 5 / stage 29; **non sappiamo cosa sia**.
- **Non** abbiamo ancora avviato nessuna missione.

**Prossimi passi, in ordine:**
1. Cliccare la riga giusta per GAME (azione 7, probabilmente `click(4)` per via dello sfasamento +1: verificare
   con `menu_info()` e a schermo) e vedere cosa parte.
2. Scoprire la variabile dello stadio da cui GAME legge (candidata `[0x800b8b00]`, stampata come `STAGE%d`),
   scriverla con `wr32` PRIMA del click; provare lo stadio di Fighter's Honor (indice 32 nella tabella titoli,
   ma l'indice dello stadio potrebbe essere 1-based o diverso: verificare col briefing a schermo).
3. Se lo stadio parte con salvataggio vuoto (niente aerei/punti), valutare di riempire il blocco di
   avanzamento (SCOPERTE #11) per avere l'aereo giusto; per i dati di missione non serve.
4. Con la missione in corso: log delle letture DAT, watchpoint su nemici/waypoint/trigger → `mission.json`.

**Come riprendere (passi esatti):**
```sh
cd ~/GitHub/ZonistationOne/run
ZS1_LUA_SCRIPT=$HOME/GitHub/AC2Remake/pipeline/lua/ac2_remote.lua ZS1_LOG_STDERR=1 SDL_VIDEODRIVER=x11 \
  ../ZoniStation_One ../roms/SCPH-7502.BIN --game="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin" \
  2>&1 | tee /tmp/remote.log
# nella finestra: Space per saltare le FMV fino al titolo; dopo ~50-60 s compare ROOT MENU in alto a sinistra
echo 'menu_info()' > /tmp/ac2_cmd.lua     # il risultato appare nel log con prefisso [R]
```
Attenzioni: se il gioco entra in **modalità demo** sul titolo i valori cambiano (è già successo); non usare
`pkill -f "ZoniStation_One ..."` (uccide anche la shell che lo contiene: usare il PID); `ac2_remote.lua` dopo
l'ultima modifica (click con breakpoint) **non è stato rieseguito**; il savestate dell'utente è locale a quella
macchina (non in git). Il `ROOT MENU` si vede in alto a sinistra con glifi sporchi: è normale.

**Idea in sospeso (non decisa):** un pannello "AC2" nel debug workspace dell'emulatore (ImGui, sul branch
`feature/lua-memory-write`) con pulsanti per aprire il menu, scegliere lo stadio e mostrare le variabili. Il debug
workspace ha già una *Lua Console* con esecuzione di codice e di file. Rimandato a dopo la prima missione avviata.

## Ambiente: cosa serve su una macchina nuova
| Cosa | Dove sta | Come si ottiene |
|---|---|---|
| Questo repo | GitHub (privato) `ZioZoni95/AC2Remake` | `git clone` |
| Emulatore | GitHub `ZioZoni95/ZonistationOne`, **branch `feature/lua-memory-write`** | `git clone` + `git checkout feature/lua-memory-write` + `make` (dipendenze: README dell'emulatore, SDL3) |
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
Godot 4.7.2 ✅, Unity Hub 4.0.0 ✅ (Editor non installato), binutils MIPS ✅, Java 21 ✅;
Ghidra 12.2 e JDK 25 ✅; Unity Editor in installazione (non verificato che sia finita); Unity su Ubuntu 26.04 non è nell'elenco ufficiale.

## Errori già fatti (da non ripetere)
- Avviare l'emulatore senza `--game`. 
- Scansione ricorsiva dei TIM senza validare la lunghezza: migliaia di falsi positivi.
- Header del modello letto come 16 B (sono 8) e numero di vertici stimato a occhio.
- Decoder TIM 4bpp con indice pixel `c//4` (era `c//2`); la fixture solo 16bpp non lo vedeva.
- Letto l'header dell'entry 0 dall'inizio del DAT invece che da +2048.
