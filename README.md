# AC2Remake — remake modernizzato di una missione di Ace Combat 2

Piano: **pipeline unica, due motori in competizione**.

```
pipeline/    strumenti Python: disco .bin → asset
mission/     descrizione della missione come DATI (waypoint, spawn, trigger) — nessun motore
assets/      glTF + PNG + WAV, validi per Godot e Unity
engines/     engines/godot (prima implementazione), engines/unity (valutazione successiva)
```

## Regole

1. **Nulla di proprietario viene distribuito.** Asset estratti dal disco (Namco/Sony) restano qui,
   per uso personale. Una eventuale pubblicazione richiede asset rifatti originali.
2. La logica di missione vive in `mission/` come dati leggibili da entrambi i motori, non in
   GDScript né in C#.
3. Il motore si decide a vertical slice finita: la stessa missione monta in Godot 4 e, se serve,
   in Unity (editor Linux) con gli stessi file.

## Fasi

- [ ] Estrazione: elenco file del disco, TIM → PNG, TMD → glTF, XA/CDDA → WAV
- [ ] Reverse-engineering script missione (savestati + probe Lua su ZoniStationOne)
- [ ] Slice Godot 4: volo arcade + nemici + trigger + HUD
- [ ] Paragone Unity sulla stessa slice
