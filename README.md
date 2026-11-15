# AC2Remake — remake modernizzato di una missione di Ace Combat 2

Remake di **una singola missione**, *Fighter's Honor*, di Ace Combat 2 (Namco 1997, PAL `SCES-00699`),
con asset estratti dal disco originale **per uso personale** e resa modernizzata. Piano: una pipeline
unica che produce glTF, PNG, WAV e dati di missione, e due motori: **Godot 4** (principale) e **Unity**
(confronto).

Il repo è privato e contiene solo codice, script e documentazione: **nessun asset del gioco è versionato**.

## Stato (2026-11-15, fine giornata)

| Fase | Stato |
|---|---|
| 0. Fondamenta (pipeline, riferimenti, emulatore) | ✅ |
| 1. Mappatura disco e archivio ACE2 | ✅ |
| 2. Asset | ✅ 24 aerei, blocco di Fighter's Honor, terreno (104k poligoni), 64 tracce audio XA; ⚠️ banco sonoro originale non trovato (effetti segnaposto) |
| 3. Reverse della missione | ▶️ **si avvia dal titolo**; tabelle T1–T9 decodificate; interprete MIPS in C eseguito sul codice originale (0 byte di differenza sulle unità); da fare: semantica manovre/rotte |
| 4. Slice giocabile in Godot 4 | ▶️ demo di volo (HUD, camera cabina/esterna, musica, esplosioni) e vista dal vivo con il codice originale; da fare: comportamento originale dentro Godot (joypad/tempo, caricamento dal DAT), flusso titolo/briefing |
| 5. Confronto con Unity | ⬜ opzionale |

Dettaglio, problema aperto e prossimi passi: [docs/CONTESTO.md](docs/CONTESTO.md).

## Per cominciare

Prerequisiti **non in git** (vanno messi a mano): il disco `Ace Combat 2 (Europe).bin` in
`~/GitHub/ZonistationOne/games/` e il BIOS PAL `SCPH-7502.BIN` in `~/GitHub/ZonistationOne/roms/`.
L'emulatore ([ZonistationOne](https://github.com/ZioZoni95/ZonistationOne)) sta in un repo separato; serve il
**`master`** aggiornato (dal 2026-11-14, commit `c59eb77`, include `emu.write_u8/16/32`).

```sh
git clone <questo repo> ~/GitHub/AC2Remake && cd ~/GitHub/AC2Remake
./tools/bootstrap.sh                 # clona/compila l'emulatore e controlla cosa manca
./tools/install_re_tools.sh          # Java, Ghidra, binutils MIPS      (sudo)
./tools/install_godot.sh             # Godot 4                          (senza sudo)
./tools/install_unity_hub.sh         # Unity Hub                        (sudo)

python3 pipeline/tests/test_pipeline.py        # 18/18
D="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"
python3 -I pipeline/ac2_extract.py iso    "$D"               out/iso      # DAT, STH, EXE
python3 -I pipeline/ac2_extract.py tims   out/iso/ACE2.DAT   out/tim     # 2.876 PNG
python3 -I pipeline/ac2_extract.py models out/iso/ACE2.DAT   out/models  # 146 glTF, ~15 s
python3 -I pipeline/ac2_aircraft.py export XFA-27 out/aerei               # un aereo giocabile (o `all`)
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor --subdiv 1 # blocco di Fighter's Honor (+ unità lisce)
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144   # terreno con texture originali
python3 -I pipeline/ac2_audio.py tracks "$D" out/iso/ACE2.STH out/audio                        # 64 tracce audio XA
./tools/sync_godot_assets.sh && godot --path engines/godot res://scenes/flight_demo.tscn       # demo (tutti i comandi: docs/GODOT.md §14)
./run_emulator.sh "Ace Combat 2 (Europe).bin"                            # il gioco
```

Tutti i comandi, i tasti dell'emulatore, il controllo remoto da Lua e il disassemblaggio con Ghidra sono in
**[docs/GUIDA.md](docs/GUIDA.md)**. Gli script di installazione e `bootstrap.sh` non sono ancora stati
provati su una macchina pulita.

## Struttura

```
pipeline/       strumenti Python (solo stdlib): CD raw + ISO9660, XA→WAV, TIM→PNG, modelli AC2→glTF,
                archivio ACE2.DAT/STH/STP, estrazione in blocco (ac2_extract), mini disassemblatore MIPS
pipeline/lua/   sonde per l'emulatore (stage, menu di debug, controllo remoto)
pipeline/ghidra/ script Ghidra headless (SetGp, DecompileAt, RefsTo)
tools/          script di installazione e bootstrap
mission/        la missione come DATI (spawn, waypoint, trigger), neutra rispetto al motore
engines/        engines/godot (principale), engines/unity (confronto)
docs/           documentazione (vedi sotto)
out/ assets/    estratti dal disco: MAI versionati
run_emulator.sh lancia ZonistationOne con disco, X11 forzato
CLAUDE.md       contesto e regole per Claude Code su una macchina nuova
```

## Documenti

| Documento | Contenuto |
|---|---|
| [docs/CONTESTO.md](docs/CONTESTO.md) | **da leggere per primo su un altro PC**: stato, problema aperto, come riprendere |
| [docs/GODOT.md](docs/GODOT.md) | **uso di Godot** nel progetto: struttura, comandi usati, visualizzatore (PS1 fedele / moderno), errori già fatti |
| [docs/STRUMENTI.md](docs/STRUMENTI.md) | **tutti gli strumenti** usati e da scaricare: versione, fonte, comando di installazione, stato |
| [docs/RECUPERO_ASSET.md](docs/RECUPERO_ASSET.md) | **recuperare asset e strumenti su un altro PC**, passo per passo con i numeri attesi |
| [docs/MULTI_PC.md](docs/MULTI_PC.md) | **lavorare su più PC**: cosa è in git, cosa no, come riprendere |
| [docs/GUIDA.md](docs/GUIDA.md) | **come si usa tutto**: installazione, emulatore, estrazione, Ghidra (comandi verificati) |
| [docs/SCOPERTE.md](docs/SCOPERTE.md) | registro delle scoperte sul disco e sul codice, con prove (#1–#39) |
| [docs/PIPELINE.md](docs/PIPELINE.md) | strumenti e formati: CD, TIM, container DAT, modello 3D di AC2, XA, archivio |
| [docs/ROADMAP.md](docs/ROADMAP.md) | fasi con gate verificabili, rischi e rimedi |
| [docs/METODOLOGIA_RE.md](docs/METODOLOGIA_RE.md) | come si reverse-ingegnerizza la missione (prima dinamico, poi statico) |
| [docs/DECISIONI.md](docs/DECISIONI.md) | registro delle scelte e dei motivi (D1–D14) |

## Regole

1. **Uso personale.** Asset e marchi sono di Namco/Sony: nulla di estratto esce da questa macchina
   (`out/`, `assets/`, `*.bin`, `*.mcd` sono ignorati). Prima di ogni push controlla `git ls-files`.
2. La logica di missione vive in `mission/` come dati leggibili da entrambi i motori.
3. Ogni scoperta di reverse va in `docs/SCOPERTE.md` con prova riproducibile; ogni scelta in `docs/DECISIONI.md`.
4. L'emulatore è di norma riferimento in sola lettura; se serve modificarlo (D8, D12) si lavora su un branch
   dedicato e il merge in `master` lo fa l'utente. `emu.write_u8/16/32` è già in `master`.
5. L'emulatore si avvia **sempre col disco** (mai solo col BIOS).
6. Nei documenti ✅ = provato sul disco reale, ⚠️ = non ancora provato.
