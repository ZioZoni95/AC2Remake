# Pipeline di estrazione — AC2Remake

Strumenti in `pipeline/` per trasformare l'immagine CD di Ace Combat 2 (Europe) in asset
utilizzabili da qualunque motore (Godot 4, Unity). Nessuna dipendenza esterna: solo stdlib Python.

## Componenti

| Strumento | Funzione | Test |
|---|---|---|
| `psxcd.py` | lettore CD raw 2352, filesystem ISO9660 (list/extract), classificazione settori mode1/mode2-form1/form2 | ✅ fixture |
| `xa_audio.py` | carving dei settori XA-audio per (file,canale) + decoder ADPCM → WAV | ✅ fixture |
| `tim2png.py` | immagini TIM (4/8/16/24 bpp, CLUT BGR555) → PNG | ✅ fixture |
| `tmd2gltf.py` | modelli TMD → OBJ + glTF 2.0 | ✅ fixture (calibrare layout su file reali) |
| `ace2arc.py` | directory dell'archivio ACE2.DAT / ACE2.STH→STP, estrazione per indice, sniff TIM/TMD | ✅ fixture |
| `pngout.py` | scrittore PNG RGB (stdlib zlib), usato da tim2png | — |
| `tests/test_pipeline.py` | fixture sintetiche: immagine CD, TIM, TMD, XA, directory ACE2 | 15/15 |

## Uso

```sh
# tutto il contenuto del filesystem ISO del disco
python3 pipeline/psxcd.py list "…/Ace Combat 2 (Europe).bin"
python3 pipeline/psxcd.py extract DISCO out/iso

# audio XA: scan di tutto il disco, un WAV per (file, canale)
python3 -c "import psxcd, xa_audio; d=psxcd.Disc('DISCO'); print(xa_audio.carve(d))"

# archivio di gioco (dopo aver estratto ACE2.DAT e ACE2.STH)
python3 pipeline/ace2arc.py list DAT ACE2.DAT
python3 pipeline/ace2arc.py extract DAT ACE2.DAT 42 out/dat
python3 pipeline/ace2arc.py list STH ACE2.STH

# asset
python3 pipeline/tim2png.py TIMFILE out.png
python3 pipeline/tmd2gltf.py TMDFILE          # → .obj + .gltf accanto

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

## Regole operative

1. **Nessun asset estratto va versionato o pubblicato** (in `.gitignore`): `assets/` e i
   blob di gioco restano locali, uso personale.
2. Prima si calibra un decoder su dati reali, poi si fidano dei suoi output: ogni tool
   parte con ipotesi marcate `CALIBRAZIONE`.
3. Ogni fixture testata sul sintetico deve riprodurre identica struttura su disco reale
   prima di considerare la pipeline "chiusa".
