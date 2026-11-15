#!/usr/bin/env python3
"""ac2_music_playlist — la playlist musicale di uno stadio, letta dai dati dell'overlay 0 (SCOPERTE #38; uso personale).

  ac2_music_playlist.py [CODICE_STADIO]        default 0x21 = Fighter's Honor (codici 1..33)

Legge out/overlay0.bin (base 0x80018000): tabella A (s16[34] @0x80018360), tabella B (s16[34] @0x800183a4), template di 9 voci (@0x800183e8).
Le voci 0 e 1 sono A[stadio] e B[stadio]; le altre sono fisse. Ogni voce = traccia di ACE2.STH = out/audio/traccia_NN_chC.wav (se presente).
Atteso per 0x21: [13, 3, 30, 31, 22, 30, 31, 25, 26]; la 13 e' "Dystopia" (confermata all'ascolto).
"""
import glob, os, struct, sys, wave

BASE = 0x80018000


def main():
    st = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x21
    o = open("out/overlay0.bin", "rb").read()
    A = struct.unpack_from("<34h", o, 0x80018360 - BASE); B = struct.unpack_from("<34h", o, 0x800183a4 - BASE)
    T = list(struct.unpack_from("<9i", o, 0x800183e8 - BASE))
    if 1 <= st <= 33:
        T[0], T[1] = A[st], B[st]
    print("stadio 0x%x playlist %s" % (st, T))
    files = {int(os.path.basename(f).split("_")[1]): f for f in glob.glob("out/audio/traccia_*_ch*.wav")}
    tot = 0
    for i, n in enumerate(T):
        f = files.get(n)
        d = 0.0
        if f:
            w = wave.open(f); d = w.getnframes() / w.getframerate(); tot += d
        print("  voce %d -> traccia %2d  %s %s" % (i, n, ("%.1f s" % d) if f else "(WAV assente)", os.path.basename(f) if f else ""))
    print("durata totale della playlist: %.1f s" % tot)


if __name__ == "__main__":
    main()
