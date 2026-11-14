#!/usr/bin/env python3
"""ac2_sfx_placeholder — effetti sonori SEGNAPOSTO sintetizzati (solo libreria standard). NON sono gli effetti originali: il banco
sonoro del gioco non e' ancora stato localizzato (vedi SCOPERTE #33). Scrive out/audio/sfx_*.wav: motore (ciclo), lancio missile,
esplosione, bip di aggancio.   Uso: ac2_sfx_placeholder.py [OUTDIR]"""
import math, os, random, struct, sys, wave

R = 22050


def write(path, xs):
    w = wave.open(path, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(R)
    w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x)) * 30000)) for x in xs)); w.close()


def lp(xs, a):
    y = 0.0; out = []
    for x in xs:
        y += a * (x - y); out.append(y)
    return out


def main(out="out/audio"):
    os.makedirs(out, exist_ok=True)
    random.seed(7)
    n = R                                                         # motore: 1 s periodico (armoniche di 55 Hz + rumore filtrato)
    noise = lp([random.uniform(-1, 1) for _ in range(n)], 0.12)
    eng = [0.35 * math.sin(2 * math.pi * 55 * t / R) + 0.2 * math.sin(2 * math.pi * 110 * t / R) + 0.12 * math.sin(2 * math.pi * 165 * t / R)
           + 0.9 * noise[t] for t in range(n)]
    for i in range(2000):                                         # raccordo agli estremi per il ciclo
        k = i / 2000; eng[i] = eng[i] * k + eng[n - 2000 + i] * (1 - k)
    write(os.path.join(out, "sfx_motore.wav"), [0.55 * x for x in eng])
    n = int(R * 1.3)                                              # lancio: soffio che scende
    nz = [random.uniform(-1, 1) for _ in range(n)]
    write(os.path.join(out, "sfx_lancio.wav"), [lp(nz, 0.05 + 0.5 * math.exp(-i / 2500))[i] * math.exp(-i / 9000) * 1.6 for i in range(n)])
    n = int(R * 2.2)                                              # esplosione: tonfo + rombo che decade
    nz = lp([random.uniform(-1, 1) for _ in range(n)], 0.06)
    write(os.path.join(out, "sfx_esplosione.wav"), [(nz[i] * 2.2 + 0.8 * math.sin(2 * math.pi * 45 * i / R)) * math.exp(-i / 11000) for i in range(n)])
    n = int(R * 0.14)                                             # bip di aggancio
    write(os.path.join(out, "sfx_aggancio.wav"), [0.5 * math.sin(2 * math.pi * 1300 * i / R) * (1 - i / n) for i in range(n)])
    print("scritti 4 effetti segnaposto in", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out/audio")
