# Decisioni di progetto

Registro delle scelte fatte, col perché. Ultima in fondo, mai cancellare.

## D1 — Repo separato dall'emulatore
**Data**: 2026-11-14. **Scelta**: il remake vive in `~/GitHub/AC2Remake`, `ZonistationOne`
è riferimemento in sola lettura (binario, BIOS, disco, psx-spx).
**Perché**: l'emulatore è il progetto dell'utente (branch master su cui lavora ad altro);
mescolare remake e emulatore sporcherebbe entrambi.

## D2 — Asset estratti MAI versionati
**Scelta**: `assets/`, `out/`, `*.bin` esclusi da git.
**Perché**: modelli/texture/audio di Namco/Sony — versionarli sarebbe distribuzione
di materiale protetto. Il repo remoto può contenere solo codice e dati missione riscritti.

## D3 — Dual-engine: Godot 4 prima, Unity come valutazione
**Scelta**: vertical slice in Godot 4, poi montaggio della stessa missione in Unity con
gli stessi asset (glTF) e gli stessi dati (mission.json); decisione a confronto.
**Perché**: vincoli concreti — GTX 1050 Mobile 4 GB regge bene Godot, male Lumen/Nanite;
scene Godot testuali co-editabili con l'agente; asset glTF sono standard per entrambi.

## D4 — La missione come dati, non come codice
**Scelta**: spawn/waypoint/trigger in `mission/mission.json` (formato neutro).
**Perché**: il porto Godot↔Unity costa solo il rendering layer; il gameplay è identico.

## D5 — Reverse-engineering dynamic-first
**Scelta**: debugger/probe Lua dell'emulatore prima, objdump poi, Ghidra solo se serve.
**Perché**: osservare il gioco vero elimina le ipotesi; i formati già documentati in
psx-spx (archivio ACE2, TIM, TMD, XA) riducono il reverse al solo contenuto custom.

## D6 — Pipeline solo stdlib Python
**Scelta**: nessuna dipendenza esterna (niente Pillow, niente PyPI).
**Perché**: zero attrito d'installazione, ambiente già complesso (emulatore, motore);
i formati PSX sono semplici abbastanza da decodificarli a mano.

## D7 — Fixtura-before-reale
**Scelta**: ogni decoder nasce con un test su fixture sintetica prima di toccare il disco.
**Perché**: un bug di parsing sul disco vero è indistinguibile da un formato inatteso;
sul sintetico i due casi si separano.
