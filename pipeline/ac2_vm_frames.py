#!/usr/bin/env python3
"""ac2_vm_frames — esegue N fotogrammi del codice originale nell'interprete MIPS con tasti iniettati (uso personale).

  ac2_vm_frames.py STATO.bin N TASTI [--out OUT.bin]

STATO.bin = stato catturato a missione in corso (pipeline/lua/ac2_capture_call.lua). TASTI = maschera joypad PS1
(0x10 su, 0x40 giu, 0x80 sinistra, 0x20 destra, 0x4000 X, 0x2000 cerchio, 0x1000 start...). Per ogni fotogramma: scrive
i tasti (invertiti) nel buffer pad a 0x800b9040, esegue FUN_8005f6a4 (lettura pad) e FUN_8002a1f4 (fotogramma),
come il ciclo originale (0x8002a154). Stampa posizione e angoli del giocatore (0x800bc5a0). SCOPERTE #34.
"""
import os, struct, subprocess, sys, tempfile

VM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mipsvm", "mipsvm")
HDR = 140  # 35 parole: 32 registri, pc, hi, lo


def step(state, btn, tmp):
    o = HDR + 0xb9040
    state[o:o + 4] = bytes([0, 0x41, (~btn) & 0xff, (~btn >> 8) & 0xff])
    a, m, b = (os.path.join(tmp, n) for n in ("a.bin", "m.bin", "b.bin"))
    open(a, "wb").write(state)
    subprocess.run([VM, a, "8005f6a4", "80010000", "1000000", m], capture_output=True, check=True)
    subprocess.run([VM, m, "8002a1f4", "8002a16c", "5000000", b], capture_output=True, check=True)
    return bytearray(open(b, "rb").read())


def player(state):
    w = struct.unpack_from("<12i", state, HDR + 0xbc5a0)
    return [w[0] / 2048, w[1] / 2048, w[2] / 2048, w[4], w[5], w[6]]


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__); sys.exit(2)
    n, btn = int(a[1]), int(a[2], 0)
    st = bytearray(open(a[0], "rb").read())
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(n):
            st = step(st, btn, tmp)
            if k % 10 == 0 or k == n - 1:
                print(k, [round(x, 1) for x in player(st)])
    if "--out" in a:
        open(a[a.index("--out") + 1], "wb").write(st)


if __name__ == "__main__":
    main()
