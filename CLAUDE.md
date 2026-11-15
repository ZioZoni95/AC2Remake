# CLAUDE.md — AC2Remake

Remake modernizzato di **una singola missione** di Ace Combat 2 (Namco 1997, PAL, `SCES-00699`):
la missione scelta è **FIGHTER'S HONOR** (l'ultima del gioco). Pipeline di estrazione in Python
(solo stdlib) + motore **Godot 4** (principale) e **Unity** (confronto). Uso personale: asset e
marchi sono di Namco/Sony.

**Per riprendere il lavoro su una macchina nuova leggi, nell'ordine:**
1. `docs/CONTESTO.md` — stato attuale, prossimi passi, come ricostruire l'ambiente; **`docs/RECUPERO_ASSET.md`** — guida passo per passo per recuperare asset e strumenti su un altro PC
2. `docs/GUIDA.md` — comandi verificati (emulatore, estrazione, disassemblaggio)
3. `docs/SCOPERTE.md` — tutto ciò che è stato scoperto sul disco (con prove)
4. `docs/GODOT.md` (uso di Godot e comandi), `docs/STRUMENTI.md` (software da installare) e `docs/MULTI_PC.md` (lavoro su più macchine)
5. `docs/DECISIONI.md`, `docs/ROADMAP.md`, `docs/METODOLOGIA_RE.md`, `docs/PIPELINE.md`

## Regole (le ha date l'utente, valgono sempre)

- **L'emulatore si avvia SEMPRE col disco** (`./run_emulator.sh "Ace Combat 2 (Europe).bin"`), mai col
  solo BIOS: una prova senza gioco non dice nulla.
- **Nulla di estratto dal disco entra in git** (`out/`, `assets/`, `*.bin`, `*.mcd`). Prima di ogni push
  verifica `git ls-files`.
- **Niente righe `Co-Authored-By` né "Generated with" nei commit** (richiesta esplicita dell'utente).
- L'emulatore (`~/GitHub/ZonistationOne`, repo separato) è riferimento in sola lettura. Se serve modificarlo
  si lavora su un branch dedicato e **il merge in `master` lo fa l'utente**, mai Claude. `emu.write_u8/16/32`
  (commit `c59eb77`) è già in `master`.
- Ogni scoperta va in `docs/SCOPERTE.md` con la prova riproducibile; ogni scelta in `docs/DECISIONI.md`.
- Non confermare mai come fatto ciò che non è stato eseguito: nei documenti ✅ = provato sul disco reale,
  ⚠️ = non ancora provato.
- Commit e push solo quando l'utente li chiede. Lingua: italiano.

## Comandi rapidi

```sh
python3 pipeline/tests/test_pipeline.py     # 18/18
python3 -I pipeline/ac2_extract.py iso|tims|models ...   # estrazione (vedi docs/GUIDA.md)
python3 -I pipeline/ac2_aircraft.py all out/aerei        # 24 aerei con texture
python3 -I pipeline/ac2_mission.py extract 32 out/fh     # Fighter's Honor (stadio 32)
python3 -I pipeline/ac2_terrain.py mesh out/fh out/fh/terreno 262144   # terreno; audio: ac2_audio.py tracks; demo: godot --path engines/godot res://scenes/flight_demo.tscn
# elenco completo e aggiornato dei comandi e dei tasti: docs/GODOT.md §14
./run_emulator.sh "Ace Combat 2 (Europe).bin"
```

## Cose non ovvie

- Disco, BIOS (`roms/SCPH-7502.BIN`) e `out/` **non sono nel repo**: vanno copiati/rigenerati (CONTESTO.md).
- Le entry di `ACE2.DAT` sono container annidati; i modelli NON sono TMD (formato in PIPELINE.md / SCOPERTE #8).
- Gli indirizzi chiave del codice sono in `docs/GUIDA.md` §4 e in SCOPERTE (#10–#23). Fighter's Honor si avvia dal titolo
  scrivendo `[0x80010030]=32`, `[0x80010034]=0`, `[0x800b83fc]=4`, `[0x800b892c]=1` (GUIDA §2b).
- Il Python va lanciato con `-I` quando legge dati del disco (regola di sicurezza dell'ambiente).
