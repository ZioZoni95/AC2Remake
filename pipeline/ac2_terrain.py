#!/usr/bin/env python3
"""ac2_terrain — altezza del suolo di una missione, replica di FUN_8002703c (uso personale, output NON versionato).

  ac2_terrain.py DIR_MISSIONE OUT [PASSO [MEZZO_LATO]]   DIR_MISSIONE = cartella di ac2_mission.py extract (part00/03/04.bin);
  PASSO in unita' (default 1024), MEZZO_LATO = ritaglio centrato in (0,0) (default 524288 = tutto il mondo)

Formato (SCOPERTE #30): parte 0 = [N][offset x N]: offset 0..255 = tessere (strutture con magic 0x5907 a short[3], short[0] = quota
base), offset 256 = mappa 256x256 di indici di tessera; parte 3 = per tessera 64 short (celle 8x8 da 512 unita') = indice del blocco
in parte 4; parte 4 = blocchi da 16 byte = 4x4 campioni (128 unita') di altezza (byte, 0 = piu' alto). Mondo: x in [-524288, 524288),
z in (-524288, 528384]; y verso il basso. Scrive terreno.png (grigi), terreno.i16 (altezza = -y, int16 LE, riga = z crescente) e terreno.json.
"""
import json, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pngout  # noqa: E402


class Terrain:
    def __init__(self, d):
        self.p0 = open(os.path.join(d, "part00.bin"), "rb").read()
        self.p3 = open(os.path.join(d, "part03.bin"), "rb").read()
        self.p4 = open(os.path.join(d, "part04.bin"), "rb").read()
        n = struct.unpack_from("<I", self.p0, 0)[0]
        offs = struct.unpack_from("<%dI" % n, self.p0, 4)
        self.tiles = list(offs[:256]) + list(offs[257:])
        self.map = self.p0[offs[256]:offs[256] + 65536]

    def y(self, x, z):
        """Quota y (verso il basso, come il gioco) del suolo in (x, z) in unita' di mondo."""
        u = (x + 0x80000) >> 12
        v = (0x81000 - z) >> 12
        u = (u & 7) if u < 0 else ((u & 7) + 0xf8 if u > 0xff else u)
        v = (v & 7) if v < 0 else ((v & 7) + 0xf8 if v > 0xff else v)
        t = self.map[v * 256 + u]
        off = self.tiles[t] if t < len(self.tiles) else 0
        if t == 0 or struct.unpack_from("<h", self.p0, off + 6)[0] != 0x5907:
            return (-0x20000 >> 11) + 30
        base = struct.unpack_from("<h", self.p0, off)[0] * 0x1000
        tile_off = struct.unpack_from("<i", self.p3, 4 + 4 * t)[0]
        a = x + 0x180000; b = -z + 0x181000
        cell = struct.unpack_from("<h", self.p3, tile_off + (((b >> 9) & 7) * 8 + ((a >> 9) & 7)) * 2)[0]
        h = self.p4[cell * 16 + ((b >> 5) & 0xc) + ((a >> 7) & 3)] * -0x10000
        return ((min(h, base) - 0x20000) >> 11) + 30


def main(d, out, step=1024, half=524288):
    T = Terrain(d)
    os.makedirs(out, exist_ok=True)
    n = 2 * half // step
    xs = [-half + i * step for i in range(n)]
    zs = [-half + j * step for j in range(n)]      # z crescente
    H = [[-T.y(x, z) for x in xs] for z in zs]        # altezza (su = positivo)
    lo = min(min(r) for r in H); hi = max(max(r) for r in H)
    open(os.path.join(out, "terreno.i16"), "wb").write(b"".join(struct.pack("<%dh" % n, *r) for r in H))
    rows = [bytes(int(255 * (v - lo) / max(hi - lo, 1)) for v in r for _ in (0, 1, 2)) for r in H]
    pngout.write_png(os.path.join(out, "terreno.png"), n, n, rows)
    json.dump({"passo": step, "lato": n, "x0": -half, "z0": -half, "altezza_min": lo, "altezza_max": hi,
               "nota": "altezza = -y di mondo; riga j <-> z = z0 + j*passo; colonna i <-> x = x0 + i*passo"},
              open(os.path.join(out, "terreno.json"), "w"), indent=1)
    print(f"terreno {n}x{n} passo {step}: altezza {lo}..{hi} unita' -> {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1024, int(sys.argv[4]) if len(sys.argv) > 4 else 524288)
