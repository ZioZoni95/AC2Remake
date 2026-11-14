# Pipeline di estrazione — AC2Remake

Strumenti in `pipeline/` per trasformare l'immagine CD di Ace Combat 2 (Europe) in asset
utilizzabili da qualunque motore (Godot 4, Unity). Nessuna dipendenza esterna: solo stdlib Python.

## Componenti

| Strumento | Funzione | Test |
|---|---|---|
| `psxcd.py` | lettore CD raw 2352, filesystem ISO9660, classificazione settori mode1/mode2-form1/form2. **Solo libreria, nessuna CLI** (`list_all`, `extract_file`) | ✅ fixture + disco reale |
| `xa_audio.py` | carving dei settori XA-audio per (file,canale) + decoder ADPCM → WAV | ✅ fixture |
| `tim2png.py` | immagini TIM (4/8/16/24 bpp, CLUT BGR555) → PNG | ✅ fixture 16bpp+4bpp; ~2.876 TIM reali |
| `tmd2gltf.py` | modelli TMD standard → OBJ + glTF 2.0. **I modelli di AC2 non sono TMD**: usare `acemodel.py` | ✅ fixture |
| `ace2arc.py` | directory dell'archivio ACE2.DAT / ACE2.STH→STP, estrazione per indice, sniff TIM/TMD | ✅ fixture |
| `ac2_aircraft.py` | i 24 aerei giocabili per nome o id (`list`, `export XFA-27 OUT`, `all OUT`): glTF texturizzato + OBJ | ✅ 24/24 |
| `mipsvm/` | interprete MIPS R3000 + GTE per eseguire il codice originale su uno snapshot (SCOPERTE #31): `gcc -O2 -o mipsvm mipsvm.c gte.c gte_ops.c` | ✅ 0 diff sulle unità |
| `ac2_export_godot.py` | `parte2_tabelle.json` → `mission.json` per la scena Godot (40 unità T1 con posizione, categoria, squadra, tipo; punti T2) | ✅ FH |
| `ghidra/ExportAll.java` | decompila tutte le funzioni di un binario in un file C + indice (base del reverse del codice di missione) | ✅ |
| `ac2_snapshot.py` | snapshot di RAM/VRAM di una missione in corso → elenco unità (JSON), mappa dall'alto, VRAM in PNG | ✅ FH |
| `ac2_mission.py` | blocco dati di una missione (`extract STADIO OUT`): parti grezze, TIM→PNG, VRAM ricostruita, modelli delle unità texturizzati, manifest | ✅ stadio 32 |
| `ac2_extract.py` | estrazione in blocco dal disco: `iso`, `tims` (2.876 PNG), `models` (146 glTF texturizzati) | ✅ disco reale |
| `mipsdis.py` | mini disassemblatore MIPS R3000 (stdlib) per sbirciare overlay ed EXE | ✅ |
| `acemodel.py` | modelli AC2 (non TMD): vertici + GT3/GT4 → OBJ; formato in SCOPERTE #8 | ✅ fixture + 146 geometrie reali |
| `pngout.py` | scrittore PNG RGB (stdlib zlib), usato da tim2png | — |
| `tests/test_pipeline.py` | fixture sintetiche: immagine CD, TIM 16/4bpp, TMD, XA, directory ACE2, geometria e glTF AC2 | 18/18 |

## Uso

```sh
# filesystem ISO del disco (il modulo è una libreria: si usa da Python)
python3 -I -c "import sys; sys.path.insert(0,'pipeline'); import psxcd; d=psxcd.Disc(sys.argv[1]); [print(p,e.lba,e.size) for p,e in psxcd.list_all(d)]" "…/Ace Combat 2 (Europe).bin"
# estrazione di un file: psxcd.extract_file(disc, entry, 'out/iso')

# audio XA: scan di tutto il disco, un WAV per (file, canale)
python3 -c "import psxcd, xa_audio; d=psxcd.Disc('DISCO'); print(xa_audio.carve(d))"

# archivio di gioco (dopo aver estratto ACE2.DAT e ACE2.STH)
python3 pipeline/ace2arc.py list DAT ACE2.DAT
python3 pipeline/ace2arc.py extract DAT ACE2.DAT 42 out/dat
python3 pipeline/ace2arc.py list STH ACE2.STH

# asset
python3 pipeline/tim2png.py TIMFILE out.png
python3 pipeline/tmd2gltf.py TMDFILE          # TMD standard → .obj + .gltf accanto
# modello AC2 (entry DAT, sotto-file N) → OBJ; glTF texturizzato: acemodel.to_gltf(m, tim_bytes, base)
python3 pipeline/acemodel.py out/iso/ACE2.DAT 179 1 out/models/e179_1.obj

# test
python3 pipeline/tests/test_pipeline.py
```

## Formati (fonte: psx-spx, clone in `~/GitHub/ZonistationOne/psx-spx.github.io`)

### Settore CD raw (2352 byte)
- 0..11 sync `00 FF×10 00`, 12..15 header BCD min/sec/frame + mode
- mode1: dati 2048 a +16 (EDC+ECC 288) — filesystem ISO
- mode2: subheader 8 a +16 (file, channel, submode, codinginfo), poi:
  - form1 (submode bit5=0): 2048 dati a +24
  - form2 (bit5=1): 2324 (0x914) a +24 — XA audio/video
- submode: bit0 EOR, bit1 Video, bit2 **Audio**, bit3 Data, bit4 Trigger, bit5 **Form2**, bit6 RT, bit7 EOF
- codinginfo audio: bit0 stereo, bit2 rate (0=37800, 1=18900 Hz), bit4-5 8bit, bit6 emphasis

### XA-ADPCM (psx-spx *CDROM XA Audio ADPCM Compression*)
- settore: 18 porzioni da 128 byte (2304) + 20 pad
- porzione: header 16 B (byte 4..7 = shift/filtro dei 4 blocchi, copie a 0..3 e 8..11)
  + 28 word 32-bit; nibble del blocco b nella word j → byte `16+b+j*4`
- 4bit: `shift = 12 - (hdr & 0x0F)`, `filtro = (hdr>>4)&3`
- `s = (t << shift) + (old*f0 + older*f1 + 32)/64`, clamp ±32768/32767
- filtri: pos (0,60,115,98,122), neg (0,0,-52,-55,-60); filtro 0 = nessuna retroazione
- stereo: nibble basso Left / alto Right; mono: due metà in sequenza

### TIM
- magic u32 0x10; flag: bit0-2 pixel mode (0=4bpp,1=8bpp,2=16bpp,3=24bpp,4=mixed), bit3 CLUT
- blocchi (`u32 len, s16 x, s16 y, u16 w, u16 h`): CLUT poi immagine; `w` in unità 16-bit
  (4bpp→4px/unità, 8bpp→2, 16bpp→1); pixel BGR555, bit15 STP ignorato

### TMD
- magic u32 0x41; flag u32; nobj u32; per oggetto 7×u32 (vertTop/Count, normTop/Count,
  primTop/Count, scale 16.16); vertice/normale 3×s16 + pad
- primitiva: u32 flag — bit30-31 mode (0=tri,1=quad), bit27-29 rate, bit24-26 mode2
- **da calibrare sui file reali di AC2**: mapping rate→(nvert,nnorm) e ordine dei campi
  (oggi: `{0:(3,1), 1:(3,3), 2:(4,1), 3:(4,4)}`, flat=normale+colore in coda,
  gouraud=normale e colore per vertice, textured=uv dopo ogni vertice). Se un indice
  esce range, l'oggetto è scartato con warning — si aggiusta la tabella, non si crasha.

### Archivio Ace Combat 2 (psx-spx *CDROM File Archive Ace Combat 2 and 3*)
```
ACE2.DAT  dati (directory all'inizio dello stesso file)
ACE2.STH  directory per i dati in ACE2.STP (streaming: audio canali 0-6, video ch8)
directory: u32 unknown(1), u32 N, poi N × u64:
  bit 0-27  size (DAT: size/4 → ×4; STP: size/800h → ×2048)
  bit 28-31 type/canale
  bit 32-63 offset/800h
```
I file **non hanno nomi**: si identificano per indice, canale e sniff del contenuto.

### Container annidati di ACE2.DAT (SCOPERTE #3)
Le entry del DAT (226) non sono file singoli: sono container `[N][offset × N]` oppure
`[size_totale][N][offset × N]`, con offset relativi all'entry; i sotto-file possono essere a loro
volta container. Un TIM è valido solo se `8 + blocco CLUT + blocco immagine` ≤ lunghezza del sotto-file
(la scansione ricorsiva senza questo controllo produce migliaia di falsi positivi). Entry 0 e 1 sono
`PS-X EXE` (codice/overlay), non container. Corrispondenza disco: `lba = 74 + offset_entry/2048`.

### Modello 3D di AC2 (SCOPERTE #8, #9) — NON è TMD
Sotto-file `[3][off×3]`: part0 = 64 B (ignoto), part1 = geometria, part2 = TIM 4bpp con CLUT.
```
geometria:  +0 u32 ?, +4 u16 ?, +6 u16 offset primitive
            +8  vertici 8 B: s16 x, y, z, 0   (fino all'offset primitive; PSX: y verso il basso)
            primitive, riconosciute dal byte-codice a +7:
              0x34 GT3 28 B: i0 i1 i2 pad | 3×(r g b code) | u0 v0 clut | u1 v1 tpage | u2 v2 pad
              0x3C GT4 36 B: i0 i1 i2 i3  | 4×(r g b code) | u0 v0 clut | u1 v1 tpage | u2 v2 pad | u3 v3 pad
```
Texture: la pagina (`tpage`: x=(t&15)·64 word, y=((t>>4)&1)·256) è la finestra VRAM in cui il TIM
viene caricato; `clut` (x=(c&3F)·16, y=c>>6) sceglie una delle palette da 16 colori della riga CLUT.
Colore 0x0000 = trasparente; colore vertice 128 = neutro. Validato su 146 geometrie reali.

## Regole operative

1. **Nessun asset estratto va versionato o pubblicato** (in `.gitignore`): `assets/` e i
   blob di gioco restano locali, uso personale.
2. Prima si calibra un decoder su dati reali, poi si fidano dei suoi output: ogni tool
   parte con ipotesi marcate `CALIBRAZIONE`.
3. Ogni fixture testata sul sintetico deve riprodurre identica struttura su disco reale
   prima di considerare la pipeline "chiusa".
