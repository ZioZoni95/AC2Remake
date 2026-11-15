---
name: feedback-working-style
description: "Come lavorare con l'utente su AC2Remake: lingua, brevita', commit/push, co-autore, installazioni, limiti d'uso"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 36c25cc4-9b6d-4286-919f-11a27efbbb66
  modified: 2026-11-14T19:51:40.815Z
---

- **Lingua italiana**, risposte **brevi** (stile caveman: l'utente lo usa perche' i token di output pesano sul limite d'uso a finestre di 5 ore). Dire onestamente cosa e' verificato (✅) e cosa no (⚠️); non confermare come fatto cio' che non e' stato eseguito.
- **Commit e push solo quando l'utente li chiede** ("commit e push"). **Mai** righe `Co-Authored-By` ne' "Generated with" nei commit (richiesta esplicita): prima di ogni push controllare `git ls-files` (nessun asset del gioco: `out/`, `assets/`, `*.bin`, `*.wav`, `*.gltf`, `*.png` estratti).
- **Software di terze parti da scaricare/eseguire** (es. `tools/install_upscaler.sh`, Real-ESRGAN): il sistema di permessi blocca l'esecuzione automatica; preparare lo script e farlo lanciare all'utente con `bash tools/...`.
- **L'emulatore si avvia sempre con il disco** (`--game=`), mai solo col BIOS. Modifiche a `ZonistationOne` solo su un branch dedicato; il merge in `master` lo fa l'utente.
- Prima di lanciare una scena Godot chiudere le finestre vecchie: **piu' finestre aperte fanno crollare gli FPS** (l'utente l'ha notato).
- Non usare `pkill -f` con il nome dell'emulatore nel comando (uccide anche la propria shell): usare il PID. I comandi alla sonda Lua si scrivono in un file temporaneo e poi `mv` (scrittura atomica).

**Why:** correzioni e richieste dell'utente nella sessione del 2026-11-14.
**How to apply:** vale per ogni sessione futura su questo progetto; le regole sono anche in `CLAUDE.md` del repo.
