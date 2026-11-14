# Roadmap — remake missione Ace Combat 2

Piano a fasi con gate espliciti. Ogni fase si chiude solo con una consegna verificabile.

## Fase 0 — Fondamenta ✅
- [x] Repo `AC2Remake` separato, piano dual-engine (Godot 4 prima, Unity come valutazione)
- [x] Pipeline di estrazione scritta e testata su fixture (15/15): psxcd, xa_audio, tim2png,
      tmd2gltf, ace2arc
- [x] Riferimenti: psx-spx clonato (specifiche + sezione archivio AC2), duckstation_ref al
      commit del README dell'emulatore
- [x] Emulatore funzionante (ZoniStationOne, source read-only), launcher `run_emulator.sh`
- [x] Documentazione: PIPELINE.md, METODOLOGIA_RE.md, DECISIONI.md, questa roadmap

## Fase 1 — Mappatura disco e archivio ✅
- [x] Inventario ISO del disco reale (5 file; via API `psxcd.list_all`, il modulo non ha CLI)
- [x] `ace2arc list` DAT (226 entry) + STH (68 entry); le entry DAT sono container annidati
- [x] Estrazione sniffata in `out/` (NON versionata): ~2.876 TIM → PNG, 146 geometrie di modello
- [x] **Gate**: inventario scritto in `docs/SCOPERTE.md` (#1–#9) ✅ (resta aperta l'anomalia offset STH, #5)

## Fase 2 — Asset ▶️
- [x] ~~Calibrazione TMD~~ superata: i modelli AC2 NON sono TMD; formato proprio decodificato (`acemodel.py`, SCOPERTE #8)
- [~] Modelli → glTF texturizzato: export pronto (SCOPERTE #9); da fare: identificare aereo giocatore e nemici della missione, verificare variante sub3 (TIM a 992,384)
- [~] Texture: TIM → PNG fatto (decoder validato, bug 4bpp corretto); da classificare per uso (terreno/HUD/aerei)
- [ ] Audio: XA → WAV (radio/annunci, musica missione), CDDA se presente
- [ ] **Gate**: un aereo + un nemico renderizzati in Godot con le texture giuste

## Fase 3 — Reverse-ing. missione ▶️ (scelta: **Fighter's Honor**, ultima missione secondo l'utente)
- [x] Missione scelta e titoli/briefing localizzati nel DAT (SCOPERTE #10)
- [x] `emu.write_u8/16/32` nell'emulatore (commit c59eb77, ora in `master` dell'emulatore) per forzare lo stato da una sonda
- [x] Trovato il formato del salvataggio (860 B + checksum a somma byte, blocco vivo a `[0x801de228]+0x8b4`, SCOPERTE #11)
- [ ] Dump del blocco di avanzamento al menu; decodifica dei campi (missioni completate, aerei, punti, flag Free Mission)
- [ ] **Avvio diretto della missione senza savestate**: dal log del caricamento disco (letture LBA ↔ entry DAT) trovare variabile stadio/flag di sblocco, poi forzarla con `emu.write_*`
- [ ] Verificare l'ordine reale (la tabella titoli la dà come 1ª, l'utente come ultima)
- [ ] Savestate pre-load missione + watchpoint sul loader DAT
- [ ] Identificazione tabelle spawn/waypoint/trigger in RAM
- [ ] Decoder dedicato → `mission/mission.json`
- [ ] **Gate**: mission.json riproduce eventi nell'ordine osservato in emulazione

## Fase 4 — Slice Godot 4
- [ ] Scena volo arcade (modello di volo semplificato, camera, HUD)
- [ ] Nemici + trigger letti da mission.json
- [ ] Audio integrato
- [ ] **Gate**: la missione è giocabile start→obiettivo→fine in Godot 4 su questa macchina

## Fase 5 — Valutazione Unity
- [ ] Import degli stessi glTF + mission.json in Unity (editor Linux)
- [ ] Confronto scritto (iterazione, resa, ergonomia) → decisione motore
- [ ] **Gate**: decisione documentata in DECISIONI.md

## Fase 6 — Chiusura
- [ ] Pulizia: nessun asset proprietario versionato (verifica `git ls-files`)
- [ ] README finale con video/screenshot della slice

## Rischio e rimedi

| Rischio | Rimedio |
|---|---|
| TMD di AC2 usa layout non standard | calibrazione con emulator+watchpoint su lettura modelli |
| Dati missione compressi/criptati nel DAT | tracciare la decompressione in RAM via probe Lua |
| Logica missione troppo incastrata nell'EXE | solo allora: Ghidra statica |
| GLES/vr di Godot su GTX 1050 | si lavora a risoluzione nativa PSX-like, upscale opzionale |

## Aggiornamento 2026-11-14 (fine sessione)
- **Fase 2**: ✅ 24 aerei giocabili con texture (`ac2_aircraft.py`); ✅ blocco di Fighter's Honor con 49 texture e 13
  unità texturizzate (`ac2_mission.py`); ✅ texture TIM verificate al 100% contro la VRAM del gioco. Restano: audio
  dal disco reale, import in Godot (gate: un aereo + un nemico con le texture giuste).
- **Fase 3**: ✅ **Fighter's Honor avviata dal titolo senza completare il gioco** (SCOPERTE #12–#18), ricetta salvata in
  `pipeline/lua/ac2_start_fighters_honor.lua` e in GUIDA §2b. Restano: nemici/waypoint/trigger → `mission.json`.
