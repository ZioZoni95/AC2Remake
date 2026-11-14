# Strumenti usati e da scaricare

Elenco di **tutto** il software che serve al progetto, con la versione con cui è stato provato (macchina di origine:
Ubuntu 26.04, GTX 1050 Mobile 4 GB, 2026-11-14), la fonte e il comando di installazione. Stato: ✅ installato e usato,
⚠️ installato ma non ancora usato a fondo, ❌ da scaricare. Gli script in `tools/` si lanciano dalla radice del repo.

## Di base (già nel sistema)

| Strumento | A cosa serve | Versione | Installazione |
|---|---|---|---|
| Git + accesso GitHub | repo `AC2Remake` (privato) e `ZonistationOne` | — | `sudo apt install git` |
| Python 3 | tutta la pipeline (solo libreria standard, regola D6) | 3.x di sistema | già presente; lanciare con `-I` |
| Compilatore C e librerie | per compilare l'emulatore | gcc, make, SDL3, GLEW | vedi README di ZonistationOne |

## Emulatore e riferimenti (repo separato `ZonistationOne`)

| Cosa | Note | Stato |
|---|---|---|
| ZonistationOne (emulatore PS1 in C) | `master` ha `emu.write_u8/16/32` dal commit `c59eb77`; `make` per compilare | ✅ |
| BIOS PAL `SCPH-7502.BIN` | **non in git**: copiare in `ZonistationOne/roms/` | ✅ |
| Disco `Ace Combat 2 (Europe).bin` | **non in git**: copiare in `ZonistationOne/games/` (usare il `.bin`, non il `.cue`) | ✅ |
| `psx-spx.github.io` (specifiche PSX) | clone di riferimento dentro `ZonistationOne/` | ✅ |

## Reverse engineering

| Strumento | Versione | Fonte | Installazione | Stato |
|---|---|---|---|---|
| binutils MIPS (`mipsel-linux-gnu-objdump`) | di sistema | apt | `./tools/install_re_tools.sh` (sudo) | ✅ |
| Java (OpenJDK) | 21 e 25 | apt | idem | ✅ |
| Ghidra | 12.2 (build 2026-10-16) | github.com/NationalSecurityAgency/ghidra/releases | idem | ✅ (headless) |
| `pipeline/mipsdis.py` | — | nel repo | niente | ✅ |

Plugin PSX di Ghidra (`ghidra_psx_ldr`): **non usato** (per i nostri blob grezzi non serve); da valutare solo per le chiamate alla libreria Sony.

## Motori e grafica

| Strumento | Versione | Fonte | Installazione | Stato |
|---|---|---|---|---|
| Godot | 4.7.2 stabile (Forward+) | github.com/godotengine/godot/releases | `./tools/install_godot.sh` (senza sudo, verifica SHA-512) | ✅ |
| Unity Hub | 4.0.0 | repo apt `hub.unity3d.com/linux/repos/deb` | `./tools/install_unity_hub.sh` (sudo) | ✅ |
| Unity Editor | 6000.6.9f1 | dal Hub (*Installs → Install Editor*), serve un account Unity | manuale | ⚠️ installato, mai avviato; Ubuntu 26.04 non è nell'elenco ufficiale |

## Modernizzazione degli asset (Livelli 1–3 del piano, vedi GUIDA §2d)

| Strumento | Versione | Fonte | Installazione | Stato |
|---|---|---|---|---|
| **Real-ESRGAN ncnn-vulkan** (upscaling texture con rete neurale, GPU via Vulkan) | build Ubuntu `20220424` (release `v0.2.5.0`, ~45 MB con modelli) | github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0 | `./tools/install_upscaler.sh` (senza sudo) | ✅ installato dall'utente, usato sull'XFA-27 (il download automatico da parte di Claude era stato bloccato dai permessi: va lanciato a mano con `bash tools/install_upscaler.sh`) |
| `tools/upscale_gltf.py` (applica Real-ESRGAN a tutte le texture di un glTF) | — | nel repo | niente | ✅ |
| Suddivisione e normali morbide | — | `pipeline/acemodel.py` (`--smooth`, `--subdiv N`) | niente | ✅ |

Modelli di Real-ESRGAN inclusi nello zip: `realesrgan-x4plus` (foto), `realesrgan-x4plus-anime`, `realesr-animevideov3`. Per texture
PS1 a 16 colori vanno provati più modelli e confrontati a vista (rischio: ammorbidire pannelli e linee nette).

## Dentro l'emulatore

Lua 5.4 incorporato (nessuna installazione). Sonde in `pipeline/lua/`; il canale di comando usa `io` (file `/tmp/ac2_cmd.lua`).

## Come ricostruire tutto su una macchina nuova

1. `git clone` di AC2Remake e `./tools/bootstrap.sh` (clona e compila ZonistationOne, controlla cosa manca).
2. Copiare **a mano** BIOS e disco (non sono in git).
3. `./tools/install_re_tools.sh`, `./tools/install_godot.sh`, `./tools/install_unity_hub.sh`, `./tools/install_upscaler.sh`.
4. Rigenerare `out/` (docs/GUIDA.md §3) e copiare gli asset in Godot con `./tools/sync_godot_assets.sh`.

Gli script di installazione e `bootstrap.sh` sono stati provati sulla macchina di origine, non su una macchina pulita.
Dettagli del lavoro su più PC: `docs/MULTI_PC.md`.
