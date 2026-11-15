# Lavorare su più PC

Il progetto si usa da più macchine. Qui c'è cosa viaggia con il repo, cosa no, e come riprendere senza perdere nulla.

## Cosa sta in git (si ritrova con `git clone`)

Codice (`pipeline/`, `engines/godot` senza asset, `tools/`), documentazione (`docs/`, `README.md`, `CLAUDE.md`), sonde Lua e
script Ghidra, memoria di Claude (`docs/memoria_claude/`) e i **savestate** (`savestati/`, eccezione voluta dall'utente, repo privato). **Mai** altri asset del gioco:
`out/`, `assets/`, `engines/godot/assets/`, `*.bin`, `*.mcd` sono ignorati. Prima di ogni push: `git ls-files | grep -iE '\.(bin|dat|png|gltf|obj|dis|mcd|zst)$'`
deve dare solo `savestati/slot*.zst`.

## Cosa NON viaggia (va ricreato o copiato)

| Cosa | Come |
|---|---|
| Disco `Ace Combat 2 (Europe).bin` e BIOS `SCPH-7502.BIN` | copiare a mano (`ZonistationOne/games/`, `ZonistationOne/roms/`) |
| `out/` (estratti, disassemblati, progetto Ghidra) | rigenerare: **`docs/RECUPERO_ASSET.md`** (passo per passo, con i numeri attesi) |
| `out/fh_start.bin` (stato di inizio missione, 2 MB) e `out/codice_leggibile/` (scritto a mano) | **copiare a mano** (il primo si può ricatturare, il secondo no) |
| `engines/godot/assets/` | `./tools/sync_godot_assets.sh` dopo aver rigenerato `out/` |
| Savestate | **in git** (`savestati/`): copiarli in `ZonistationOne/run/savestates/` (RECUPERO_ASSET §12) |
| Memory card, log (`ZonistationOne/run/`) | non servono |
| Cronologia delle conversazioni con Claude e la sua memoria locale (`~/.claude/...`) | **non viaggiano**: tutto ciò che serve sta in `CLAUDE.md` e `docs/` |
| Software (Ghidra, Godot, Unity, Real-ESRGAN, Java) | `docs/STRUMENTI.md` |

## Layout atteso

`~/GitHub/AC2Remake` e `~/GitHub/ZonistationOne` affiancati (`run_emulator.sh` e `bootstrap.sh` lo danno per scontato).
`ZonistationOne` deve essere su `master` aggiornato (contiene `emu.write_*`).

## Come riprendere su un PC nuovo (in ordine)

1. Leggere `CLAUDE.md` (regole) e `docs/CONTESTO.md` (stato e prossimi passi); i comandi stanno in `docs/GUIDA.md`.
2. Seguire "Come ricostruire tutto" in `docs/STRUMENTI.md`.
3. Verifica: `python3 pipeline/tests/test_pipeline.py` (18/18); poi `ac2_extract.py models …` (attesi 146 modelli, 0 saltati).
4. `git pull` all'inizio di ogni sessione, `git push` alla fine (solo quando lo decide l'utente).

## Convenzioni di lavoro da rispettare ovunque

- Emulatore **sempre col disco**; nessun `Co-Authored-By` nei commit; commit e push solo su richiesta dell'utente.
- Ogni scoperta in `docs/SCOPERTE.md` con la prova; ogni scelta in `docs/DECISIONI.md`; ✅ = provato, ⚠️ = non provato.
- I comandi alla sonda remota si scrivono in un file temporaneo e poi `mv` (scrittura atomica).
- Non usare `pkill -f` con il nome dell'emulatore (uccide anche la propria shell): usare il PID.
- Le modifiche all'emulatore su un branch dedicato; il merge in `master` lo fa l'utente.

## Differenze tra macchine da tenere d'occhio

GPU e driver (la macchina di origine è un portatile ibrido Intel + NVIDIA GTX 1050; l'emulatore forza X11), versione di Ubuntu
(26.04: Unity non è nell'elenco ufficiale), spazio disco (gli estratti occupano qualche centinaio di MB, le texture ingrandite di più).
