"""Modello 3D di Ace Combat 2 (sotto-file dei container DAT, es. entry 179..190).

Formato ricavato per reverse-ing. (docs/SCOPERTE.md #8), NON TMD standard.
Contenitore: [N][offset x N] (offset relativi al sotto-file). Per un aereo N=3:
  part0 = 64 B (non decodificato), part1 = geometria, part2 = TIM (texture, 4bpp+CLUT).
Geometria:
  +0x00 header 8 B: u32 ?, u16 ?, u16 offset primitive
  +0x08 vertici: 8 B = (s16 x, s16 y, s16 z, s16 0), fino all'offset primitive
  poi primitive consecutive, riconosciute dal byte-codice a +7:
    0x34  GT3  28 B: i0 i1 i2 pad | 3x(r g b code) | u0 v0 clut | u1 v1 tpage | u2 v2 pad
    0x3C  GT4  36 B: i0 i1 i2 i3  | 4x(r g b code) | u0 v0 clut | u1 v1 tpage | u2 v2 pad | u3 v3 pad
  (indici di vertice a 1 byte; la tabella termina a fine parte)
"""
import struct, sys, os


def split(blob):
    n = struct.unpack_from("<I", blob, 0)[0]
    offs = list(struct.unpack_from("<%dI" % n, blob, 4)) + [len(blob)]
    return [blob[offs[i]:offs[i + 1]] for i in range(n)]


def _prims(g, o):
    tris, quads = [], []
    while o + 28 <= len(g):
        code = g[o + 7]
        if code == 0x34 and g[o + 3] == 0:
            i = tuple(g[o:o + 3]); col = [tuple(g[o + 4 + 4 * k:o + 7 + 4 * k]) for k in range(3)]
            uv = [(g[o + 16], g[o + 17]), (g[o + 20], g[o + 21]), (g[o + 24], g[o + 25])]
            tris.append((i, col, uv)); o += 28
        elif code == 0x3C and o + 36 <= len(g):
            i = tuple(g[o:o + 4]); col = [tuple(g[o + 4 + 4 * k:o + 7 + 4 * k]) for k in range(4)]
            uv = [(g[o + 20], g[o + 21]), (g[o + 24], g[o + 25]), (g[o + 28], g[o + 29]), (g[o + 32], g[o + 33])]
            quads.append((i, col, uv)); o += 36
        else:
            break
    return tris, quads, len(g) - o


def parse_geometry(g):
    """Header 8 B: u32 (non decodificato), u16 (non decodificato), u16 = offset primitive.
    Vertici da +8 fino all'offset primitive."""
    prim_off = struct.unpack_from("<H", g, 6)[0]
    if prim_off < 8 or (prim_off - 8) % 8:
        raise ValueError("offset primitive non valido")
    nv = (prim_off - 8) // 8
    verts = [struct.unpack_from("<3h", g, 8 + 8 * i) for i in range(nv)]
    tris, quads, tail = _prims(g, prim_off)
    mx = max([max(t[0]) for t in tris] + [max(q[0]) for q in quads] + [0])
    if tail != 0 or mx >= nv:
        raise ValueError(f"geometria incoerente (tail={tail}, maxidx={mx}, nv={nv})")
    return {"verts": verts, "tris": tris, "quads": quads, "tail": 0}


def to_obj(m, path):
    with open(path, "w") as f:
        for x, y, z in m["verts"]:
            f.write(f"v {x} {-y} {z}\n")        # PSX: y verso il basso
        for i, _, uv in m["tris"]:
            f.write("f %d %d %d\n" % tuple(k + 1 for k in i))
        for i, _, uv in m["quads"]:
            a, b, c, d = (k + 1 for k in i)
            f.write(f"f {a} {b} {d} {c}\n")      # ordine PSX a Z → anello


if __name__ == "__main__":
    dat, entry, sub, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    d = open(dat, "rb").read(8 + 226 * 8)
    import ace2arc
    _, ents = ace2arc.parse_dir(d, "DAT")
    e = ents[entry]
    with open(dat, "rb") as f:
        f.seek(e["off"]); blob = f.read(e["size"])
    parts = split(blob)
    m = parse_geometry(split(parts[sub])[1])
    print(len(m["verts"]), "verts", len(m["tris"]), "GT3", len(m["quads"]), "GT4", "tail", m["tail"])
    to_obj(m, out)
