---
name: project-ac2remake-stato
description: "Stato di AC2Remake a fine sessione 2026-11-14: obiettivo, cosa e' fatto, cosa manca, dove ripartire"
metadata:
  node_type: memory
  type: project
  originSessionId: 36c25cc4-9b6d-4286-919f-11a27efbbb66
  modified: 2026-11-15T15:02:59.200Z
---

Obiettivo: remake in Godot 4 della missione **Fighter's Honor** (stadio 32, ultima) di Ace Combat 2 (PAL, uso personale, repo privato `ZioZoni95/AC2Remake`), con **comportamento originale** (stesso codice del gioco) e **grafica modernizzata**. Unity solo come confronto opzionale (D3, D13).

Fatto (2026-11-14, tutto committato e pubblicato fino a `8fed21b`): estrazione completa dal disco (aerei, missione, terreno, audio XA); Fighter's Honor si avvia dal titolo senza completare il gioco (scrittura di 4 variabili, `docs/GUIDA.md` §2b); script di missione decodificati (T1–T9); interprete MIPS in C che esegue il codice originale con 0 byte di differenza sulle unita'; terreno ridisegnato dai poligoni originali; demo giocabile Godot (HUD, camera cabina/esterna, musica XA, esplosioni originali); vista dal vivo (emulatore come motore, Godot come grafica).

Manca: comportamento originale **dentro** Godot (joypad e tempo nell'interprete, estensione Godot, caricamento dei dati dal DAT); banco sonoro originale (effetti sono segnaposto, non trovato VAB); musica giusta della missione; voci radio; palette del terreno come le schiarisce il gioco; verifica dell'allineamento z/unita'; HUD e flusso (titolo, briefing) originali.

**Musica di Fighter's Honor = "Dystopia" = `out/audio/traccia_13_ch0.wav`** (voce 13 di ACE2.STH, trovata nel codice: playlist stadio 0x21 = [13,3,30,31,22,30,31,25,26]; confermata all'ascolto dall'utente il 2026-11-15). La demo Godot usa ancora la traccia sbagliata finche' non si cambia. Ordine di lavoro deciso dall'utente: logica di missione originale (Ghidra), palette, cielo e nuvole, musica, comandi per ultimi.

Fine giornata 2026-11-15: tutto pubblicato fino a `045183f`. L'utente cambia PC: guida in `docs/RECUPERO_ASSET.md` (asset + strumenti) e `docs/CONTESTO.md`. Non in git e da copiare a mano: disco, BIOS, `out/fh_start.bin`, `out/codice_leggibile/` (C leggibile derivato dal codice Namco, mai versionato).

**Why:** contesto che non sta nel codice.
**How to apply:** per riprendere leggere `CLAUDE.md`, poi `docs/CONTESTO.md` (stato e prossimi passi) e `docs/GODOT.md` §14 (comandi). Disco e BIOS NON sono in git; `out/` va rigenerato. Vedi [[feedback-working-style]] e [[feedback-emulator-always-with-game]].
