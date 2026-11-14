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

## Il problema aperto (dove ripartire)
Fighter's Honor è l'ultima missione; Free Mission si sblocca solo finendo il gioco. Strade:
1. **Menu di debug del gioco**: `ROOT MENU` con GAME/BRIEFING/TITLE/FONT, struttura a `0x800ad2e0`,
   codice a `0x80067324` (funzione `0x8006685c`, nessun chiamante diretto: viene da un dispatcher).
   Non si sa ancora come si attiva né se è raggiungibile nella versione PAL.
2. **Blocco di avanzamento del salvataggio**: 860 byte + checksum a somma di byte, copia viva a
   `[0x801de228] + 0x8b4`. Riempirlo (missioni completate, aerei, punti, flag Free Mission) con
   `emu.write_*`, oppure generare una memory card `.mcd` con checksum corretto.
3. Trovare la variabile di modalità/stadio osservando i breakpoint e forzarla con `emu.write_*`.
Passo successivo previsto: sonda Lua con breakpoint su `0x8006685c` e `0x80067324` mentre si naviga
fino al titolo/START; in parallelo Ghidra sui due binari (`docs/GUIDA.md` §4).

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
Ghidra e JDK 25 **non** ancora installati; Unity su Ubuntu 26.04 non è nell'elenco ufficiale.

## Errori già fatti (da non ripetere)
- Avviare l'emulatore senza `--game`. 
- Scansione ricorsiva dei TIM senza validare la lunghezza: migliaia di falsi positivi.
- Header del modello letto come 16 B (sono 8) e numero di vertici stimato a occhio.
- Decoder TIM 4bpp con indice pixel `c//4` (era `c//2`); la fixture solo 16bpp non lo vedeva.
- Letto l'header dell'entry 0 dall'inizio del DAT invece che da +2048.
