#!/usr/bin/env python3
"""ac2_audio — flussi audio XA di Ace Combat 2 (musica e voci, in ACE2.STP) (uso personale, output NON versionato).

  ac2_audio.py list DISCO.bin                       elenco (file, canale, settori, frequenza, stereo, durata stimata)
  ac2_audio.py extract DISCO.bin FILE CANALE OUT.wav [SECONDI]    decodifica un canale (al massimo SECONDI, default tutto)
  ac2_audio.py tracks DISCO.bin ACE2.STH OUTDIR    le 64 tracce della STH (canali interlacciati a 8 vie: ogni traccia = i settori del suo canale nel suo intervallo)

Usa xa_audio.decode_sector (ADPCM XA 4 bit). STP parte a LBA 47887 (SCOPERTE #1). Provato sul disco reale il 2026-11-14 (vedi SCOPERTE #33).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psxcd, xa_audio  # noqa: E402

STP_LBA = 47887


def scan(disc):
    streams = {}
    for lba in range(STP_LBA, disc.nsect):
        kind, data, sub = disc.sector(lba)
        if kind != "form2" or not (sub[2] & 0x04):
            continue
        key = (sub[0], sub[1])
        s = streams.setdefault(key, {"lbas": [], "coding": sub[3]})
        s["lbas"].append(lba)
    return streams


def info(s):
    cd = s["coding"]; stereo = bool(cd & 1); rate = 18900 if cd & 4 else 37800
    per = 2016 if stereo else 4032                       # campioni per canale e per settore (4 bit)
    return stereo, rate, per, len(s["lbas"]) * per / rate


def main(a):
    if len(a) >= 2 and a[0] == "list":
        d = psxcd.Disc(a[1])
        for (f, c), s in sorted(scan(d).items()):
            stereo, rate, per, dur = info(s)
            print(f"file {f:3} canale {c:2}  {len(s['lbas']):6} settori  {rate} Hz  {'stereo' if stereo else 'mono  '}  ~{dur:6.1f} s  (LBA {s['lbas'][0]}..{s['lbas'][-1]})")
    elif len(a) >= 5 and a[0] == "extract":
        d = psxcd.Disc(a[1]); f, c = int(a[2]), int(a[3])
        s = scan(d)[(f, c)]
        stereo, rate, per, dur = info(s)
        n = len(s["lbas"])
        if len(a) > 5:
            n = min(n, int(float(a[5]) * rate / per) + 1)
        samples = []
        for lba in s["lbas"][:n]:
            _k, data, _sub = d.sector(lba)
            smp, r = xa_audio.decode_sector(data, stereo, s["coding"])
            samples.extend(smp)
        xa_audio.write_wav(a[4], samples, rate, stereo)
        print(f"scritto {a[4]}: {len(samples)} campioni, {rate} Hz, {'stereo' if stereo else 'mono'}, ~{n * per / rate:.1f} s")
    elif len(a) >= 4 and a[0] == "tracks":
        import bisect, ace2arc
        d = psxcd.Disc(a[1]); ents = ace2arc.parse_dir(open(a[2], "rb").read(), "STH")[1]; streams = scan(d)
        os.makedirs(a[3], exist_ok=True)
        for e in ents:
            s = streams.get((1, e["chan"]))
            if not s: continue                          # canale 8 = video
            stereo, rate, per, _dur = info(s)
            lo = STP_LBA + e["off"] // 2048; hi = lo + e["size"] // 2048
            L = s["lbas"]; sel = L[bisect.bisect_left(L, lo):bisect.bisect_left(L, hi)]
            samples = []
            for lba in sel:
                _k, data, _sub = d.sector(lba)
                smp, _r = xa_audio.decode_sector(data, stereo, s["coding"]); samples.extend(smp)
            name = os.path.join(a[3], f"traccia_{e['idx']:02d}_ch{e['chan']}.wav")
            xa_audio.write_wav(name, samples, rate, stereo)
            print(f"{name}: {len(sel) * per / rate:5.1f} s")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
