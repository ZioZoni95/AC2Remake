# Decisioni di progetto

Registro delle scelte fatte, col perché. Ultima in fondo, mai cancellare.

## D1 — Repo separato dall'emulatore
**Data**: 2026-11-14. **Scelta**: il remake vive in `~/GitHub/AC2Remake`, `ZonistationOne`
è riferimento in sola lettura (binario, BIOS, disco, psx-spx); eccezione in D8.
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

## D8 — Modifiche all'emulatore solo su branch dedicato
**Data**: 2026-11-14. **Scelta**: D1 resta la regola (emulatore = riferimento), con una eccezione
autorizzata dall'utente: serve poter scrivere in RAM da Lua per avviare una missione specifica
senza giocare tutto il gioco. Si fa su `feature/lua-memory-write` in `ZonistationOne`
(`emu.write_u8/16/32`, solo RAM e scratchpad, BIOS rifiutato), mai su `master`, senza push.
**Perché**: le sonde in sola lettura non bastano a forzare lo stadio; un branch separato
non tocca il lavoro dell'utente su `master`.
**Limite noto**: la scrittura salta il bus (niente watchpoint, I-cache non invalidata): solo dati.

## D9 — Missione scelta: Fighter's Honor
**Data**: 2026-11-14. **Scelta**: il remake riproduce *Fighter's Honor*, l'ultima missione
secondo l'utente. **Perché**: scelta dell'utente. **Nota**: la tabella titoli nell'EXE la elenca
per prima (SCOPERTE #10): l'ordine della tabella non coincide necessariamente con l'ordine di gioco;
da verificare osservando il numero di stadio in emulazione.

## D10 — Raggiungere la missione senza savestate di forzatura
**Data**: 2026-11-14. **Scelta**: non partire da un savestate "preparato"; osservare i log del
caricamento da disco (letture CD/LBA mappate sulle entry DAT) e ricavare come il gioco sceglie lo
stadio, per poi avviarlo direttamente. Un savestate F5 resta ammesso solo come comodità *dopo* aver
raggiunto la missione. **Perché**: indicazione dell'utente; capire la selezione stadio serve anche
a rintracciare gli asset della missione.

## D11 — L'emulatore si avvia sempre col disco
**Scelta**: ogni prova parte con `--game=<AC2 .bin>`. **Perché**: una prova col solo BIOS non
dice nulla sul remake (errore fatto e corretto il 2026-11-14).

## D12 — Le funzioni di scrittura Lua sono in master dell'emulatore
**Data**: 2026-11-14. **Fatto**: l'utente ha fuso `feature/lua-memory-write` in `master` di `ZonistationOne`
(avanzamento rapido, `master` = `c59eb77`, già su `origin/master`). **Conseguenza**: D8 resta valida per il
metodo (modifiche all'emulatore su un branch dedicato, merge a cura dell'utente) ma non serve più il checkout del
branch per usare `emu.write_*`: basta `master`. Il branch remoto `feature/lua-memory-write` esiste ancora.

## D13 — Modernizzazione degli asset dentro Godot, senza Unity
**Data**: 2026-11-14. **Scelta**: il "moderno" si ottiene con materiali, luci e post-elaborazione in Godot (già visibile nel
visualizzatore, tasto `M`) e con una pipeline di asset in tre livelli: (1) **texture ingrandite con Real-ESRGAN** (ncnn-vulkan,
GPU), (2) **geometria più morbida** (normali morbide + suddivisione di Phong, `acemodel --smooth/--subdiv`), (3) **materiali PBR**
(rugosità/metallo/normal map dedotte, da rifinire a mano). Primo banco di prova: **XFA-27**. **Perché**: l'utente vuole provare
prima la resa moderna con texture rifatte; il salto di qualità dipende dagli asset, non dal motore, quindi Unity non serve
(resta il confronto opzionale di D3). **Limiti noti**: le texture PS1 sono a 16 colori con linee nette (l'upscaling neurale può
ammorbidirle: provare più modelli e confrontare a vista); la suddivisione arrotonda, non aggiunge dettagli. **Vincolo**: tutto
ciò che deriva dal gioco resta fuori da git (`engines/godot/assets/` ignorata).

## D14 — Modello di upscaling: Real-ESRGAN x4plus-anime
**Data**: 2026-11-14. **Scelta**: per le texture PS1 degli aerei si usa `realesrgan-x4plus-anime` (4×, ncnn-vulkan). **Perché**: confronto a vista
su XFA-27: tiene nette le linee dei pannelli e liscia i campi piatti; `x4plus` aggiunge grana da foto, `animevideov3` sfoca. Verificato in
Godot (modalità moderna) con giudizio positivo dell'utente. **Limite**: provato su un solo aereo; i bordi possono avere aloni leggeri.
