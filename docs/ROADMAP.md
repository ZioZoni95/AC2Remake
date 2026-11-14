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

## Fase 1 — Mappatura disco e archivio
- [ ] `psxcd list` sul disco reale → inventario ISO (EXE, ACE2.*, dimostrativi)
- [ ] `ace2arc list` DAT + STH → mappa entries (tipi sniffati, canali)
- [ ] Estrazione massiva sniffata in `out/` (NON versionata)
- [ ] **Gate**: inventario scritto in `docs/SCOPERTE.md` con conteggi per tipo

## Fase 2 — Asset
- [ ] Calibrazione decoder TMD sui file reali (layout rate/flags)
- [ ] Modelli: aereo giocatore + nemici della missione → glTF
- [ ] Texture: TIM → PNG (paesaggio, HUD, interfacce)
- [ ] Audio: XA → WAV (radio/annunci, musica missione), CDDA se presente
- [ ] **Gate**: un aereo + un nemico renderizzati in Godot con le texture giuste

## Fase 3 — Reverse-ing. missione (scelta dall'utente)
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
