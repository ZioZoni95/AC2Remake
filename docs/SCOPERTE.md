# Scoperte — registro del reverse-engineering

Ogni scoperta concreta sul disco/archivio/RAM di Ace Combat 2 va qui, con data, prova e
prossimo passo. Formato: tabella crescente. Il file parte vuoto: si riempie in Fase 1.

| # | Data | Scoperta | Prova | Prossimo passo |
|---|---|---|---|---|
| 1 | 2026-11-14 | Disco ISO9660: 5 file — `ACE2.DAT` (lba 74, 97.918.976 B), `ACE2.STH` (lba 47886, 552 B), `ACE2.STP` (lba 47887, 407.377.920 B), `SCES_006.99` (lba 24, 102.400 B, EXE), `SYSTEM.CNF`. 246.952 settori | `psxcd.list_all(Disc(bin))` | — |
| 2 | 2026-11-14 | `ACE2.DAT`: 226 entry (224 ch0, 2 ch2), 97,7 MB. Entry 0 e 1 = `PS-X EXE` (overlay di codice, 657.408 e 145.408 B). Le altre 224 NON sono TIM/TMD diretti | `ace2arc list DAT`; sniff in `out/dat_sniff.tsv` | decodificare i container |
| 3 | 2026-11-14 | Le entry DAT sono **container annidati**: 153 con `[size_totale][N][N offset]`, 47 con `[N][N offset]` (N≤~11), 26 altre non classificate. I sotto-file hanno a loro volta header `[N][offset...]` | dump header entry 3, 100, 179 | parser ricorsivo |
| 4 | 2026-11-14 | Nei container: 71 TIM (magic 0x10) trovati a livello 1 (es. entry 179 sub0, 200 sub1; tipicamente 4bpp+CLUT, flag 8). **0 TMD standard (0x41)**: i modelli usano altro formato; sub-file tipo `03 00 00 00 10 00 00 00 50 …` (entry 179 sub1–4, 181) candidati modello | scan sottofile | analisi del formato modello (Fase 2) |
| 5 | 2026-11-14 | `ACE2.STH`: 68 entry (ch0:6 ch1:8 ch2:10 ch3:11 ch4:10 ch5:10 ch6:9 ch8:4); somma size 352.925.696 B, estensione max 407.316.480 B ≈ STP | `ace2arc list STH` | ANOMALIA: le prime 7 entry hanno offset 0,2048,…,12288 con size ~9 MB (sovrapposte): la regola offset STH va verificata |
| 6 | 2026-11-14 | Docs/PIPELINE.md citava `psxcd.py list/extract` da CLI: **non esiste** (il modulo è solo libreria). Si usa `psxcd.list_all`/`extract_file` | `python3 pipeline/psxcd.py list …` stampa nulla | aggiungere CLI o correggere doc |
| 7 | 2026-11-14 | Decoder TIM validato su dati reali: ~2.876 TIM (197 entry DAT, ricerca ricorsiva con tabelle di offset e dimensione TIM coerente) convertiti senza errori; texture di terreno riconoscibili (mappa isola con rilievo = e018 sub6 #11; vista aerea di pista = e131 sub8 #3). **Bug trovato e corretto**: 4bpp usava `c//4`/`(c%4)*4` invece di `c//2`/`(c%2)*4`; la fixture sintetica era solo 16bpp e non lo vedeva → aggiunto test di regressione (16/16) | `out/tim/*.png` (non versionato) | classificare TIM per uso (terreno/HUD/aerei); il 71 della scoperta 4 era il solo livello 1 |
| 8 | 2026-11-14 | **Formato modello AC2 decodificato** (non TMD): sotto-file `[3][off×3]` = part0 64 B (?), part1 geometria, part2 TIM 4bpp+CLUT. Geometria: header 8 B (`u32 ?`, `u16 ?`, `u16 offset primitive`), vertici 8 B `(s16 x,y,z,0)` da +8, poi primitive: **GT3** 28 B (code 0x34: 3 indici u8 + pad, 3×RGB+code, 3×UV + clut/tpage) e **GT4** 36 B (code 0x3C). Validazione: 146 geometrie in 47 entry DAT (179–190 e altre), consumo esatto dei byte (tail 0) e indici < n. vertici; wireframe = caccia con ali a freccia | `pipeline/acemodel.py`; render in `out/wire_top.png` | texture: part2 TIM + UV (tpage/clut); export glTF; identificare quale entry è l'aereo giocatore/nemici; part0 e 4 byte di header ignoti |

### Notazione
- Offsets RAM in esadecimale con base (es. `0x80123456`).
- Offset archivio in blocchi 800h come nel formato ACE2 (`off_raw × 2048 = byte`).
- Prova = comando/probe riproducibile (non "mi sembra").
