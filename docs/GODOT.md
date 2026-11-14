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
