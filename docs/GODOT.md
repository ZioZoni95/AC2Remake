# Godot — uso nel progetto

Guida al progetto Godot di AC2Remake (`engines/godot`) con **i comandi effettivamente usati**. Versione provata: **Godot 4.7.2
stabile**, renderer **Forward+** (Vulkan), MSAA 3D ×2, macchina Ubuntu 26.04 con GTX 1050. ✅ = eseguito e verificato,
⚠️ = non ancora provato. Per installare Godot: `./tools/install_godot.sh` (vedi `docs/STRUMENTI.md`).

## 1. Struttura del progetto

```
engines/godot/
  project.godot                 configurazione (scena principale, renderer Forward+, MSAA)
  scenes/aircraft_viewer.tscn   scena del visualizzatore (un solo nodo con lo script)
  scripts/aircraft_viewer.gd    visualizzatore degli aerei (PS1 fedele / moderno)
  assets/                       glTF e PNG copiati dal disco: NON in git (ignorata)
```

Gli asset non sono nel repo (sono materiale Namco/Sony). Si ottengono così:

```sh
python3 -I pipeline/ac2_aircraft.py all out/aerei                         # 24 aerei → out/aerei       ✅
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor          # unità di Fighter's Honor   ✅
./tools/sync_godot_assets.sh                                              # copia in engines/godot/assets   ✅
```

## 2. Comandi usati

| Scopo | Comando | Stato |
|---|---|---|
| Aprire l'editor | `godot --editor --path engines/godot` | ⚠️ non ancora usato |
| Lanciare il visualizzatore | `godot --path engines/godot` | ✅ (default: XFA-27, modalità moderna) |
| Scegliere modello e modalità | `godot --path engines/godot -- --model=res://assets/aerei/f117a.gltf --mode=psx` | ✅ (XFA-27; gli altri non guardati) |
| Importazione senza finestra | `godot --headless --path engines/godot --import` | ✅ nessun errore |
| Controllo dello script | `godot --headless --path engines/godot --check-only --script res://scripts/aircraft_viewer.gd` | ✅ |
| Avvio breve senza grafica | `godot --headless --path engines/godot --quit-after 12` | ✅ (la finestra virtuale è 64×64) |
| Catturare fotogrammi | `godot --path engines/godot --write-movie /percorso/nome.png --fixed-fps 10 --quit-after 14 -- --mode=modern` | ✅ |

Note sui comandi:
- Gli argomenti dopo `--` sono per lo script (`OS.get_cmdline_user_args()`), quelli prima per Godot.
- `--write-movie` apre per qualche secondo una **finestra vera** sullo schermo e scrive `nome00000000.png`, `nome00000001.png`, …
  più un `.wav`; `--quit-after N` chiude dopo N fotogrammi. Serve a controllare il rendering senza guardare lo schermo.
- Per forzare un driver: `--rendering-driver opengl3` (compatibilità) o `vulkan` (default con Forward+).
- Con `--headless` non c'è rendering: va bene per importare e per controllare errori di script, non per vedere il risultato.

## 3. Visualizzatore degli aerei

`scripts/aircraft_viewer.gd` carica il glTF **a runtime** (`GLTFDocument.append_from_file`), quindi non serve alcun passaggio di
importazione manuale: basta che i file siano in `assets/`. Tiene **due copie** del modello e ne mostra una alla volta.

| Modalità | Cosa fa |
|---|---|
| **PS1 fedele** (`--mode=psx`) | texture a pixel netti, ombreggiatura "cotta" dai colori vertice, nessuna luce, fondo scuro. Serve a verificare l'estrazione |
| **Moderna** (`--mode=modern`) | stessa geometria e texture, con filtro anisotropico e mipmap, luce direzionale con ombre, materiale metallico (metallic 0,45, roughness 0,4), cielo procedurale, tonemapping filmic, glow, SSAO, normali morbide |

Comandi nella finestra: frecce = orbita, rotella o `+`/`-` = zoom, `Spazio` = pausa rotazione, **`M`** = cambia modalità, `Esc` = esci.

I file `*_smooth*.gltf` (vedi §4) hanno già le normali: il visualizzatore non le rigenera.

## 4. Modernizzare la geometria

```sh
python3 -I pipeline/ac2_aircraft.py export XFA-27 out/aerei --smooth      # normali morbide      → xfa27_smooth0.gltf  ✅
python3 -I pipeline/ac2_aircraft.py export XFA-27 out/aerei --subdiv 1    # suddivisione ×4      → xfa27_smooth1.gltf  ✅
./tools/sync_godot_assets.sh
godot --path engines/godot -- --model=res://assets/aerei/xfa27_smooth1.gltf --mode=modern
```
La suddivisione usa la tessellazione di Phong (arrotonda le superfici, non aggiunge dettagli nuovi). Verificato a vista su XFA-27:
livrea bianca e rossa conservata, superfici più morbide. Texture ingrandite (✅ XFA-27, giudizio dell'utente "bellissimo"):

```sh
python3 -I tools/upscale_gltf.py out/aerei/xfa27_smooth1.gltf            # → xfa27_smooth1_hd.gltf (+ PNG ingrandite)
./tools/sync_godot_assets.sh
godot --path engines/godot -- --model=res://assets/aerei/xfa27_smooth1_hd.gltf --mode=modern
```
Dettagli e confronto dei modelli di upscaling: `docs/GUIDA.md` §2d.

## 5. Cose imparate (errori già fatti, da non ripetere)

- **L'orbita**: camera e modello come figli dello stesso nodo che ruota non cambiano mai la vista relativa. Orbita solo la camera;
  il modello resta fermo.
- **Inquadratura**: con campo visivo largo (75°) l'aereo risultava minuscolo; ora FOV 40° e distanza = 1,15 × la diagonale del modello.
- **Normali**: devono seguire il **verso dei triangoli**, non puntare "verso l'esterno" rispetto al baricentro. Con materiale a doppia
  faccia Godot inverte la normale sulle facce viste da dietro in base al winding; invertire le normali per il baricentro colora tutto
  di azzurro e cancella la livrea (provato a vista).
- **Costanti Godot**: `Environment.REFLECTED_LIGHT_SOURCE_SKY` non esiste in 4.7 (la riflessione dal cielo è già il comportamento
  predefinito). Controllare sempre con `--check-only`.
- Le coordinate originali PSX hanno **y verso il basso**; gli export la invertono e correggono il winding, la scala è 0,01 (1 unità
  PSX = 1 cm). Nei dati di gioco le posizioni sono a 32 bit con 11 bit frazionari.
- Texture trasparenti: il colore palette `0x0000` diventa alfa 0 (materiale `alphaMode MASK`).

## 6. Prossimi passi in Godot

1. Unità nemica di Fighter's Honor nel visualizzatore (gate della Fase 2). I glTF sono già in `assets/fighters_honor/` dopo la sync.
2. Texture ingrandite: ✅ fatto sull'XFA-27; da estendere agli altri 23 aerei e alle unità nemiche (stesso comando, `all`).
3. Scena di volo: camera, modello di volo arcade, HUD; poi terreno e missione (`mission/mission.json`, quando i dati saranno decodificati).
4. Stile PS1 opzionale come shader (vertex snapping, texture affini): il vincolo è la GTX 1050 da 4 GB; la modalità "fedele" attuale non
   li usa.

## 7. Scena della missione (✅ prova di visualizzazione dei dati, 2026-11-14)

**Non è una demo giocabile**: mostra le **40 unità della lista iniziale T1** di Fighter's Honor (dati del disco, SCOPERTE #27) con il modello del
loro tipo, il giocatore (XFA-27) e i 48 punti di piazzamento T2, per verificare la coerenza dei dati estratti.

```sh
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor                                              # tabelle, modelli, unità T1
python3 -I pipeline/ac2_export_godot.py out/fighters_honor/parte2_tabelle.json out/fighters_honor/mission.json   # mission.json
./tools/sync_godot_assets.sh                                                                                  # copia in engines/godot/assets
godot --path engines/godot res://scenes/mission_viewer.tscn                  # camera panoramica
godot --path engines/godot res://scenes/mission_viewer.tscn -- --cam=player   # camera dal giocatore
godot --headless --path engines/godot --check-only --script res://scripts/mission_viewer.gd                  # controllo errori
```
Cattura di fotogrammi senza guardare lo schermo: `godot --path engines/godot res://scenes/mission_viewer.tscn --write-movie /percorso/nome.png --fixed-fps 10 --quit-after 8`.

Comandi nella finestra: `WASD` muovi, `Q`/`E` giù/su, tasto destro + mouse = guarda, `Maiusc` veloce, rotella = velocità, `[` e `]` = ingrandimento dei
modelli (solo per vederli, default ×25), `L` = etichette (`#slot cCATEGORIA sSQUADRA tTIPO`), `T` = punti T2, `Esc` = esci.

Limiti: scala di mondo ipotetica (0,01 m per unità), suolo piatto a quota 0 (11 unità sono "appoggiate al suolo" e il terreno non è decodificato),
nessun orientamento delle unità, tipo del modello delle unità in volo ancora ipotetico (usato 0). `P` (segnaposto parcheggiati) non esiste più: le 5 unità
di sottotipo 25 sono unità vere e compaiono con le altre.

## 8. Demo di volo (✅ gira, 2026-11-14; semplificata)

```sh
python3 -I pipeline/ac2_terrain.py out/fighters_honor out/fighters_honor/terreno 1024 262144   # altezze del suolo
./tools/sync_godot_assets.sh
godot --path engines/godot res://scenes/flight_demo.tscn                      # demo giocabile
godot --headless --path engines/godot res://scenes/flight_demo.tscn -- --autotest   # prova senza finestra (stampa "AUTOTEST ...")
```
Comandi: su/giù beccheggio, sinistra/destra virata con rollio, `A`/`D` imbardata, `W`/`S` motore, `Spazio` missile (guida sul bersaglio in mira), `R` ricomincia, `Esc` esci.
Contiene: terreno dalle altezze originali (SCOPERTE #30), le 39 unità della T1 con il modello del loro tipo e un marcatore (rosso = nemico, verde = squadra 0),
missili, HUD, vittoria a nemici distrutti. **Non rispetta ancora il comportamento originale**: la logica è mia (aerei in cerchio, terrestri fermi, nemici che non
sparano, scala 0,02 m/unità e velocità scelte a mano). Requisito dell'utente: **usare la stessa logica del gioco**. Percorso: portare in GDScript il codice
decompilato (`out/codice/missione_completa.c`): inizializzazione unità da T1/T4/T5/T6 (`FUN_80046dfc`), interprete azioni T9 (`FUN_8005e348`), nodi di
comportamento T8 (`FUN_8005ec0c`), manovre T7 (`FUN_8005cab4` e le funzioni di manovra), obiettivi (maschere `0x800b7e84/7e80`), poi il volo del giocatore.

## 9. Terreno con poligoni e texture originali (✅ visibile, 2026-11-14)

```sh
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor                                   # (una volta) parti e texture
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144        # mesh glTF del terreno (~4 s)
./tools/sync_godot_assets.sh
godot --path engines/godot res://scenes/terrain_view.tscn                                           # visualizzatore
godot --path engines/godot res://scenes/terrain_view.tscn -- --cam=-940,900,-3500,0,-35              # camera: x,y,z (m), imbardata, beccheggio (gradi)
```
Comandi: `WASD` muovi, `Q`/`E` giù/su, tasto destro + mouse guarda, `Maiusc` veloce, rotella = velocità, `Esc`. Il terreno della demo di volo e della vista dal vivo
usa ancora le altezze colorate (§8): da sostituire con questa mesh. Limiti: orientamento di z e allineamento con le unità da verificare (SCOPERTE #32).

## 10. Missione in versione moderna (✅ 2026-11-14)

Tutto dai dati originali; versione "moderna" = texture ingrandite 4× con Real-ESRGAN, normali morbide, suddivisione 1 sui modelli, luce con ombre, SSAO, glow, cielo.

```sh
# terreno (poligoni e texture delle tessere; gli edifici dentro le tessere ci sono gia')
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144        # terreno_mesh.gltf con normali
python3 -I tools/upscale_gltf.py out/fighters_honor/terreno/terreno_mesh.gltf --model realesrgan-x4plus  # → terreno_mesh_hd.gltf (25 texture, ~2 min)
# unità della missione (aerei, strutture, veicoli): 13 modelli
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor --subdiv 1                          # unita_NN_smooth1.gltf
for f in out/fighters_honor/models/unita_*_smooth1.gltf; do python3 -I tools/upscale_gltf.py "$f" --model realesrgan-x4plus-anime; done   # *_smooth1_hd.gltf (cache: pagine condivise)
./tools/sync_godot_assets.sh
godot --path engines/godot res://scenes/terrain_view.tscn           # terreno, tasto M = PS1 fedele / moderno (--mode=psx|modern)
godot --path engines/godot res://scenes/flight_demo.tscn            # demo con terreno HD, unità HD e XFA-27 HD
```
Modelli di upscaling scelti: `realesrgan-x4plus` per il terreno (roccia, più dettaglio naturale), `realesrgan-x4plus-anime` per aerei e strutture (linee nette).
Le scene usano automaticamente `*_smooth1_hd.gltf` se presenti, altrimenti l'originale. **Difetti noti**: sottili linee bianche orizzontali nel terreno (giunzioni
tra tessere: bordi di texture o piccoli buchi), orientamento di z e allineamento unità/terreno non verificati, nebbia da tarare, oggetti statici fuori dalle
tessere (se esistono) non ancora cercati, HUD ed effetti ancora non ridisegnati.

## 11. Riepilogo completo dei comandi Godot (✅ = eseguito e verificato il 2026-11-14)

**Preparazione degli asset** (una volta, dalla radice del repo; i file vanno in `out/` e `engines/godot/assets/`, entrambi ignorati da git):
```sh
python3 -I pipeline/ac2_extract.py iso "$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin" out/iso    # ✅ DAT, STH, EXE
python3 -I pipeline/ac2_aircraft.py all out/aerei                                                                # ✅ 24 aerei
python3 -I pipeline/ac2_aircraft.py export XFA-27 out/aerei --subdiv 1                                           # ✅ geometria morbida
python3 -I tools/upscale_gltf.py out/aerei/xfa27_smooth1.gltf                                                    # ✅ texture 4× (anime)
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor --subdiv 1                                      # ✅ missione: parti, tabelle, 13 unità
python3 -I pipeline/ac2_export_godot.py out/fighters_honor/parte2_tabelle.json out/fighters_honor/mission.json  # ✅ unità T1
python3 -I pipeline/ac2_terrain.py out/fighters_honor out/fighters_honor/terreno 1024 262144                    # ✅ altezze (collisione)
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144                    # ✅ mesh del terreno
python3 -I tools/upscale_gltf.py out/fighters_honor/terreno/terreno_mesh.gltf --model realesrgan-x4plus         # ✅ terreno HD
for f in out/fighters_honor/models/unita_*_smooth1.gltf; do python3 -I tools/upscale_gltf.py "$f"; done         # ✅ unità HD
./tools/sync_godot_assets.sh                                                                                     # ✅ copia in engines/godot/assets
```

**Scene** (tutte con `godot --path engines/godot <scena>`; argomenti dopo `--`):

| Scena | Cosa mostra | Comandi |
|---|---|---|
| (predefinita) `res://scenes/aircraft_viewer.tscn` | un aereo; `--model=res://assets/aerei/xfa27_smooth1_hd.gltf --mode=psx\|modern` | frecce orbita, rotella/`+`/`-` zoom, `Spazio` pausa, `M` modalità, `Esc` |
| `res://scenes/terrain_view.tscn` | terreno con poligoni e texture originali; `--mode=psx\|modern`, `--cam=x,y,z,imbardata,beccheggio` | `WASD`, `Q`/`E`, tasto destro + mouse, `Maiusc`, rotella, `M`, `Esc` |
| `res://scenes/mission_viewer.tscn` | le 40 unità della T1 nelle posizioni originali; `--cam=player` | `WASD`, `Q`/`E`, tasto destro, `Maiusc`, `[` `]` ingrandimento, `L` etichette, `T` punti T2, `Esc` |
| `res://scenes/flight_demo.tscn` | **demo giocabile** (terreno HD con gonne, unità HD, XFA-27 moderno, HUD); `-- --autotest` stampa e chiude; `-- --cockpit` parte in cabina | su/giù beccheggio, sinistra/destra virata, `A`/`D` imbardata, `W`/`S` motore, `Spazio` missile, **`C` camera esterna/cabina**, **`+`/`-` distanza camera**, **`G` qualità (bassa/media/alta)**, **`N` traccia musicale successiva**, `R` ricomincia, `Esc`; `-- --fx` prova un'esplosione |
| `res://scenes/live_view.tscn` | **comportamento originale dal vivo**: legge `/tmp/ac2_state.bin` dall'emulatore; HUD e cabina come la demo | si pilota nell'emulatore; `C` camera, `+`/`-` distanza, `Esc` |

**Vista dal vivo** (richiede l'emulatore e il disco):
```sh
cd ~/GitHub/ZonistationOne/run
AC2_EXPORT=1 ZS1_LUA_SCRIPT=$HOME/GitHub/AC2Remake/pipeline/lua/ac2_remote.lua ZS1_LOG_STDERR=1 SDL_VIDEODRIVER=x11 \
  ../ZoniStation_One ../roms/SCPH-7502.BIN --game="$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"
# nell'emulatore: F8 (stato di Fighter's Honor, slot 0); poi, in un altro terminale:
godot --path ~/GitHub/AC2Remake/engines/godot res://scenes/live_view.tscn
```

**Utilità:**
```sh
godot --headless --path engines/godot --import                                           # ✅ importazione senza finestra
godot --headless --path engines/godot --check-only --script res://scripts/flight_demo.gd  # ✅ controllo errori di uno script
godot --headless --path engines/godot res://scenes/flight_demo.tscn -- --autotest        # ✅ prova senza finestra
godot --path engines/godot res://scenes/terrain_view.tscn --write-movie /percorso/nome.png --fixed-fps 10 --quit-after 5 -- --cam=-940,160,-3500,0,-18   # ✅ cattura (apre una finestra per qualche secondo)
godot --editor --path engines/godot                                                       # ⚠️ editor, non ancora usato
```
Costanti da tarare a mano: `WS` (0,02 m per unità di mondo), velocità (150 m/s), nebbia e camera di inseguimento in `scripts/flight_demo.gd`; ingrandimento dei modelli
in `scripts/mission_viewer.gd`; modalità e luci in `scripts/terrain_view.gd`.

## 12. HUD, camere e qualità (✅ 2026-11-14)

- **HUD** (`scripts/hud.gd`, disegnato in 2D, stile Ace Combat): bussola in alto con prua, orizzonte artificiale con scala di beccheggio che ruota col rollio,
  velocità (km/h) e quota (m) ai lati, barra motore, radar circolare (4 km) con i nemici, mirino, riquadro del bersaglio con distanza (solo nella demo: nella vista dal vivo
  il bersagliamento del gioco non è decodificato), munizioni, nemici rimasti, danno (sempre 0% per ora). I dati arrivano da `_hud_data()` in `flight_demo.gd`.
- **Camera** (`C`): esterna di inseguimento (distanza e campo visivo crescono con la velocità; nessun ritardo sulla posizione) o **cabina** (vista dal naso, modello nascosto).
- **Qualità** (`G`): 0 bassa (niente SSAO, glow, ombre, antialiasing), 1 **media** predefinita (glow, ombre vicine, FXAA), 2 alta (anche SSAO e MSAA 2×). Il terreno non proietta ombre
  (le cascate lo ridisegnavano 5 volte: era la causa principale del calo di FPS). Godot usa la GTX 1050 (verificato nel log, "Using Device #1: NVIDIA").
- **Colori**: cielo più profondo, nebbia azzurra, contrasto/saturazione (`adjustment_*`), terreno opaco senza riflessi (lo schermo era troppo bianco). Le palette ricostruite dai TIM sono più
  scure di quelle che il gioco ha in VRAM (il gioco le schiarisce a runtime: 12.582 word di CLUT diverse): da replicare, ancora non fatto.
- **Gonne del terreno**: pareti verticali dove i bordi di tessere adiacenti hanno quote diverse (coprivano le linee bianche, che erano buchi nella geometria).
- **Da fare per le prestazioni**: dividere il terreno in blocchi per il frustum culling (oggi è una sola mesh per texture), livelli di dettaglio, texture compresse.

## 13. Audio ed effetti (✅ 2026-11-14, versione segnaposto per gli effetti sonori)

- **Musica**: le tracce originali XA decodificate (`ac2_audio.py tracks`), copiate in `engines/godot/assets/audio/` da `tools/sync_godot_assets.sh` (le prime sette: `traccia_00…06`).
  Nella demo suona la traccia 00 in ciclo; **`N`** passa alla successiva (il nome è nella riga in alto). Quale sia la musica vera di Fighter's Honor non è ancora noto: ascolta e dimmi.
- **Effetti sonori**: motore (il tono segue il gas e la velocità), lancio missile, esplosione e bip di aggancio del bersaglio sono **sintetizzati** (`ac2_sfx_placeholder.py`),
  NON originali. Il banco sonoro originale non è stato localizzato (SCOPERTE #33).
- **Effetti visivi**: esplosioni con i **fotogrammi originali** (foglio dell'entry 2, `assets/fx/explosion.png`, fusione additiva, sprite rivolti alla camera) e scia di piccoli
  sbuffi dietro i missili. Prova: `godot --path engines/godot res://scenes/flight_demo.tscn -- --fx` (un'esplosione 260 m davanti all'aereo al fotogramma 12).
- Nota di test: a 150 m/s e 10 fotogrammi/s l'aereo percorre 15 m per fotogramma, quindi gli effetti vicini si attraversano in un attimo nelle catture.
- Limiti: sfondo non perfettamente nero degli sprite (leggero riquadro chiaro), esplosioni a una sola dimensione, nessuna voce radio, nessun suono nella vista dal vivo oltre a motore e musica.

## 14. Riepilogo aggiornato dei comandi (fine sessione 2026-11-14)

**Pipeline completa, nell'ordine** (dalla radice del repo; `$D` = `"$HOME/GitHub/ZonistationOne/games/Ace Combat 2 (Europe).bin"`; tutto in `out/`, ignorato da git):
```sh
python3 pipeline/tests/test_pipeline.py                                                       # test: 18/18
python3 -I pipeline/ac2_extract.py iso "$D" out/iso                                           # DAT, STH, EXE
python3 -I pipeline/ac2_extract.py tims out/iso/ACE2.DAT out/tim                              # 2.876 PNG (serve e002_1_3.png per le esplosioni)
python3 -I pipeline/ac2_aircraft.py all out/aerei                                             # 24 aerei
python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor --subdiv 1                   # missione: parti, tabelle, 13 unità lisce
python3 -I pipeline/ac2_export_godot.py out/fighters_honor/parte2_tabelle.json out/fighters_honor/mission.json
python3 -I pipeline/ac2_terrain.py out/fighters_honor out/fighters_honor/terreno 1024 262144  # altezze (collisione)
python3 -I pipeline/ac2_terrain.py mesh out/fighters_honor out/fighters_honor/terreno 262144  # mesh con texture e gonne
python3 -I pipeline/ac2_audio.py tracks "$D" out/iso/ACE2.STH out/audio                       # 64 tracce XA → WAV
python3 -I pipeline/ac2_sfx_placeholder.py                                                    # effetti sonori segnaposto
# modernizzazione (Real-ESRGAN: bash tools/install_upscaler.sh, una volta)
python3 -I tools/upscale_gltf.py out/fighters_honor/terreno/terreno_mesh.gltf --model realesrgan-x4plus
for f in out/fighters_honor/models/unita_*_smooth1.gltf; do python3 -I tools/upscale_gltf.py "$f"; done
python3 -I pipeline/ac2_aircraft.py export XFA-27 out/aerei --subdiv 1 && python3 -I tools/upscale_gltf.py out/aerei/xfa27_smooth1.gltf
./tools/sync_godot_assets.sh                                                                  # copia tutto in engines/godot/assets
```

**Scene e tasti** (`godot --path engines/godot <scena> [-- argomenti]`):

| Scena | Argomenti | Tasti |
|---|---|---|
| `res://scenes/flight_demo.tscn` (demo giocabile) | `--cockpit` parte in cabina, `--fx` prova un'esplosione, `--autotest` prova senza finestra | su/giù beccheggio, sinistra/destra virata, `A`/`D` imbardata, `W`/`S` motore, `Spazio` missile, `C` camera esterna/cabina, `+`/`-` distanza camera, `G` qualità (bassa/media/alta), `N` musica successiva, `R` ricomincia, `Esc` |
| `res://scenes/live_view.tscn` (logica originale dal vivo) | — (emulatore con `AC2_EXPORT=1`, vedi §11) | `C`, `+`/`-`, `Esc`; si pilota nell'emulatore |
| `res://scenes/terrain_view.tscn` | `--mode=psx\|modern`, `--cam=x,y,z,imbardata,beccheggio`, `--flat` (diagnostica) | `WASD`, `Q`/`E`, tasto destro + mouse, `Maiusc`, rotella, `M`, `Esc` |
| `res://scenes/mission_viewer.tscn` | `--cam=player` | `WASD`, `Q`/`E`, tasto destro, `Maiusc`, `[` `]`, `L`, `T`, `Esc` |
| `res://scenes/aircraft_viewer.tscn` | `--model=res://assets/aerei/xfa27_smooth1_hd.gltf`, `--mode=psx\|modern` | frecce, rotella/`+`/`-`, `Spazio`, `M`, `Esc` |

**Controlli e utilità:**
```sh
godot --headless --path engines/godot --import                                                       # importazione senza finestra
godot --headless --path engines/godot --check-only --script res://scripts/flight_demo.gd             # controllo errori (anche hud.gd, live_view.gd, ...)
godot --path engines/godot res://scenes/flight_demo.tscn --write-movie /percorso/nome.png --fixed-fps 10 --quit-after 20 -- --fx    # cattura (finestra per qualche secondo)
```
Attenzione: più finestre Godot aperte insieme fanno crollare gli FPS (chiudi quelle vecchie prima di lanciarne una nuova).

**Emulatore e interprete MIPS** (SCOPERTE #31):
```sh
gcc -O3 -o pipeline/mipsvm/mipsvm pipeline/mipsvm/mipsvm.c pipeline/mipsvm/gte.c pipeline/mipsvm/gte_ops.c        # compila l'interprete
./pipeline/mipsvm/mipsvm out/ac2_cpuA.bin 8002bcdc 8002a3ec 200000000 out/vm_out.bin                                # esegue FUN_8002bcdc su uno snapshot (STATO START STOP MAX OUT)
~/Tools/ghidra/support/analyzeHeadless out/ghidra AC2 -process overlay0.bin -noanalysis -scriptPath pipeline/ghidra -postScript ExportAll.java out/codice/overlay0   # tutto il codice in C
```
