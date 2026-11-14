# AC2Remake — remake modernizzato di una missione di Ace Combat 2

Remake di **una singola missione** di Ace Combat 2 (Namco 1997, PAL), con asset estratti
dal disco originale per uso personale e resa modernizzata. Piano: **pipeline unica,
due motori in competizione** (Godot 4 prima, Unity come valutazione).

## Stato (2026-11-14)

| Fase | Stato |
|---|---|
| 0. Fondamenta (pipeline, riferimenti, emulatore) | ✅ |
| 1. Mappatura disco e archivio ACE2 | ✅ (inventario in SCOPERTE #1–#6) |
| 2. Asset (modelli, texture, audio) | ▶️ in corso: TIM e modelli decodificati, glTF texturizzato; audio e import Godot da fare |
| 3. Reverse-ing. missione → `mission/mission.json` | ▶️ avviata: missione scelta **Fighter's Honor**, serve il modo di avviarla direttamente |
| 4. Slice Godot 4 giocabile | ⬜ |
| 5. Valutazione Unity | ⬜ |

## Struttura

```
pipeline/      strumenti Python (solo stdlib): CD raw + ISO9660, XA-ADPCM→WAV,
               TIM→PNG, modelli AC2→OBJ/glTF texturizzato (`acemodel`), archivio ACE2.DAT/STH/STP —
               testati 18/18
mission/       la missione come DATI (waypoint, spawn, trigger), motore-agnostico
assets/        glTF + PNG + WAV (estratti: MAI versionati, vedi .gitignore)
engines/       engines/godot (prima), engines/unity (valutazione)
docs/          PIPELINE, ROADMAP, METODOLOGIA_RE, DECISIONI, SCOPERTE
run_emulator.sh  lancia ZoniStationOne (che resta nel suo repo) con X11 forzato
```

## Documenti

| Documento | Contenuto |
|---|---|
| [docs/GUIDA.md](docs/GUIDA.md) | **come si usa tutto**: installazione, emulatore, estrazione, disassemblaggio (comandi verificati) |
| [docs/PIPELINE.md](docs/PIPELINE.md) | strumenti, uso, e i formati CD/TIM/TMD/XA/ACE2 con specifiche psx-spx |
| [docs/ROADMAP.md](docs/ROADMAP.md) | fasi con gate verificabili, rischi e rimedi |
| [docs/METODOLOGIA_RE.md](docs/METODOLOGIA_RE.md) | come si reverse-ingegnerizza la missione (dynamic-first) |
| [docs/DECISIONI.md](docs/DECISIONI.md) | registro delle scelte col perché |
| [docs/SCOPERTE.md](docs/SCOPERTE.md) | registro delle scoperte concrete (offset, prove) |

## Comandi rapidi

```sh
python3 pipeline/tests/test_pipeline.py            # test pipeline (18/18)
./run_emulator.sh                                  # menu BIOS (SCPH-7502 EU)
./run_emulator.sh "Ace Combat 2 (Europe).bin"      # disco montato
```

## Regole

1. **Uso personale.** Asset e marchi sono di Namco/Sony: nulla di estratto esce da questa
   macchina (`assets/`, `out/`, `*.bin` in `.gitignore`). Un'eventuale pubblicazione
   richiede asset rifatti originali.
2. La logica di missione vive in `mission/` come dati leggibili da entrambi i motori.
3. Ogni scoperta di reverse va in `docs/SCOPERTE.md` con prova riproducibile.
4. L'emulatore (`~/GitHub/ZonistationOne`) è di norma riferimento in sola lettura. Eccezione
   autorizzata dall'utente (2026-11-14, D8): modifiche mirate solo su un branch dedicato
   (oggi `feature/lua-memory-write`, `emu.write_u8/16/32`), mai su `master`. I probe Lua per il
   remake vivono in `pipeline/lua/`.
5. L'emulatore si avvia **sempre col disco montato** (`./run_emulator.sh "Ace Combat 2 (Europe).bin"`),
   mai solo col BIOS.
