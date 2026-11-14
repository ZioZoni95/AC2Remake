#!/usr/bin/env python3
"""ac2_terrain — altezza del suolo di una missione, replica di FUN_8002703c (uso personale, output NON versionato).

  ac2_terrain.py mesh DIR_MISSIONE OUT [MEZZO_LATO]   mesh glTF del terreno con poligoni e texture vere (tessere, SCOPERTE #32)
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


TILE = 4096


def parse_tile(P, o, nxt):
    """Tessera (SCOPERTE #32): header 16 B [short y0, y1, flag, 0x5907][byte nv_per_LOD][byte n_prim][u16 offset prim];
    vertici s16 (x,y,z,0) da +0x10, 2*nv (LOD vicino, poi lontano); prim: 0x24 = triangolo texturizzato 36 B
    [i0 i1 i2 pad][r g b code][u0 v0 clut16][u1 v1 tpage16][u2 v2 pad] + secondo set UV (12 B) + 4 B di flag;
    0x2c = quadrilatero 44 B (4 indici, 4 UV per set). Coordinate locali: mondo = centro tessera + 2*locale."""
    nv, npr = P[o + 8], P[o + 9]
    poff = struct.unpack_from("<H", P, o + 10)[0]
    verts = [struct.unpack_from("<3h", P, o + 0x10 + 8 * i) for i in range(nv)]     # solo LOD vicino
    prims = []
    q = o + poff
    for _ in range(npr):
        code = P[q + 7]
        if code == 0x24: n, rs = 3, 36
        elif code == 0x2c: n, rs = 4, 44
        else: break
        idx = tuple(P[q:q + n])
        col = tuple(P[q + 4:q + 7])
        uvs = []; clut = tpage = 0
        for k in range(n):
            base = q + 8 + 4 * k
            uvs.append((P[base], P[base + 1]))
            if k == 0: clut = struct.unpack_from("<H", P, base + 2)[0]
            if k == 1: tpage = struct.unpack_from("<H", P, base + 2)[0]
        prims.append((idx, col, uvs, clut, tpage))
        q += rs
    return verts, prims


def build_mesh(d, out, half=262144):
    """Mesh del terreno (poligoni e texture vere) nel ritaglio +-half, in out/terreno_mesh.gltf (+ PNG per tpage/clut)."""
    import acemodel, ac2_extract as X
    T = Terrain(d)
    vram = acemodel.vram_new()
    for part in ("part08.bin", "part09.bin"):
        b = open(os.path.join(d, part), "rb").read()
        for _tag, tim in X.walk(b, "p"):
            acemodel.vram_apply_tim(vram, tim)
    P = T.p0
    srt = sorted(set(T.tiles))
    cache = {}
    def tile(t):
        if t not in cache:
            o = T.tiles[t]; nxt = min([x for x in srt if x > o] + [len(P)])
            cache[t] = parse_tile(P, o, nxt)
        return cache[t]
    DROP = 3000                      # profondita' delle gonne (unita' di mondo)
    def edge(t, side):
        """Vertici del bordo (LOD vicino) di una tessera: lista (coordinata lungo il bordo, indice vertice, y locale)."""
        lv = tile(t)[0]
        if side == "E": sel = [(lz, i, ly) for i, (lx, ly, lz) in enumerate(lv) if lx == 1024]
        elif side == "W": sel = [(lz, i, ly) for i, (lx, ly, lz) in enumerate(lv) if lx == -1024]
        elif side == "N": sel = [(lx, i, ly) for i, (lx, ly, lz) in enumerate(lv) if lz == 1024]
        else: sel = [(lx, i, ly) for i, (lx, ly, lz) in enumerate(lv) if lz == -1024]
        return sorted(sel)
    OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
    verts, faces = [], []
    n_skirt = 0
    lo = (-half + 524288) // TILE; hi = (half + 524288) // TILE
    for v in range(256):
        for u in range(lo, hi):
            zc = 528384 - v * TILE - TILE // 2
            if not (-half <= zc < half): continue
            t = T.map[v * 256 + u]
            lv, prims = tile(t)
            xc = u * TILE - 524288 + TILE // 2
            b0 = len(verts)
            for (lx, ly, lz) in lv:
                verts.append((xc + 2 * lx, 2 * ly, zc + 2 * lz))
            vmap = {}
            for idx, col, uvs, clut, tpage in prims:
                faces.append((tuple(b0 + i for i in idx), [col] * len(idx), uvs, clut, tpage))
                for j, vi in enumerate(idx): vmap.setdefault(vi, (uvs[j], clut, tpage, col))
            # gonne: dove la quota del bordo non coincide con quella della tessera vicina (altrimenti si vede il cielo)
            for side, du, dv in (("E", 1, 0), ("W", -1, 0), ("N", 0, -1), ("S", 0, 1)):
                nu, nv_ = u + du, v + dv
                if not (0 <= nu < 256 and 0 <= nv_ < 256): continue
                mine = edge(t, side); theirs = edge(T.map[nv_ * 256 + nu], OPP[side])
                if [(c, ly) for c, _i, ly in mine] == [(c, ly) for c, _i, ly in theirs]: continue
                for (c1, i1, y1), (c2, i2, y2) in zip(mine, mine[1:]):
                    if i1 not in vmap or i2 not in vmap: continue
                    (uv1, cl, tp, col), (uv2, _c, _t, _k) = vmap[i1], vmap[i2]
                    k = len(verts)
                    verts.append((verts[b0 + i1][0], verts[b0 + i1][1] + DROP, verts[b0 + i1][2]))
                    verts.append((verts[b0 + i2][0], verts[b0 + i2][1] + DROP, verts[b0 + i2][2]))
                    faces.append(((b0 + i1, b0 + i2, k, k + 1), [col] * 4, [uv1, uv2, uv1, uv2], cl, tp))
                    n_skirt += 1
    m = {"verts": verts, "faces": faces}
    os.makedirs(out, exist_ok=True)
    g = acemodel.to_gltf_vram(m, vram, os.path.join(out, "terreno_mesh"), scale=0.02, smooth=True)   # normali morbide per la luce
    print(f"mesh terreno: {len(verts)} vertici, {len(faces)} poligoni ({n_skirt} segmenti di gonna), {len(set((f[4], f[3]) for f in faces))} texture -> {g}")


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
    if len(sys.argv) >= 4 and sys.argv[1] == "mesh":
        build_mesh(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 262144); sys.exit(0)
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1024, int(sys.argv[4]) if len(sys.argv) > 4 else 524288)
