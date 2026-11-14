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


def _prims(g, o, FACES=None):
    FACES = [] if FACES is None else FACES
    tris, quads = [], []
    while o + 28 <= len(g):
        code = g[o + 7]
        if code == 0x34 and g[o + 3] == 0:
            i = tuple(g[o:o + 3]); col = [tuple(g[o + 4 + 4 * k:o + 7 + 4 * k]) for k in range(3)]
            uv = [(g[o + 16], g[o + 17]), (g[o + 20], g[o + 21]), (g[o + 24], g[o + 25])]
            tris.append((i, col, uv)); FACES.append((i, col, uv, struct.unpack_from("<H", g, o + 18)[0], struct.unpack_from("<H", g, o + 22)[0])); o += 28
        elif code == 0x3C and o + 36 <= len(g):
            i = tuple(g[o:o + 4]); col = [tuple(g[o + 4 + 4 * k:o + 7 + 4 * k]) for k in range(4)]
            uv = [(g[o + 20], g[o + 21]), (g[o + 24], g[o + 25]), (g[o + 28], g[o + 29]), (g[o + 32], g[o + 33])]
            quads.append((i, col, uv)); FACES.append((i, col, uv, struct.unpack_from("<H", g, o + 22)[0], struct.unpack_from("<H", g, o + 26)[0])); o += 36
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
    faces = []
    tris, quads, tail = _prims(g, prim_off, faces)
    mx = max([max(t[0]) for t in tris] + [max(q[0]) for q in quads] + [0])
    if tail != 0 or mx >= nv:
        raise ValueError(f"geometria incoerente (tail={tail}, maxidx={mx}, nv={nv})")
    return {"verts": verts, "tris": tris, "quads": quads, "faces": faces, "tail": 0}


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


# ---------------------------------------------------------------- glTF texturizzato
import base64, json, zlib


def _png_rgba(path, w, h, rgba):
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def parse_tim4(t):
    """TIM 4bpp con CLUT -> dict(clut_xy, clut[], rect(x,y,w_px,h), idx[] indici palette per pixel)."""
    fl = struct.unpack_from("<I", t, 4)[0]
    if fl & 7 != 0 or not fl & 8:
        raise ValueError("serve TIM 4bpp con CLUT")
    pos = 8
    blen, cx, cy, cw, ch = struct.unpack_from("<IhhHH", t, pos)
    clut = [struct.unpack_from("<H", t, pos + 12 + 2 * i)[0] for i in range((blen - 12) // 2)]
    pos += blen
    blen, ix, iy, iw, ih = struct.unpack_from("<IhhHH", t, pos)
    body = t[pos + 12:pos + blen]
    w = iw * 4
    idx = bytearray(w * ih)
    for y in range(ih):
        for x in range(w):
            b = body[y * iw * 2 + x // 2]
            idx[y * w + x] = (b >> ((x % 2) * 4)) & 15
    return {"clut_xy": (cx, cy), "clut": clut, "rect": (ix * 4, iy, w, ih), "idx": idx}


def palette_image(tim, pal):
    """RGBA per la palette `pal` (indice nella riga CLUT, 16 colori ciascuna); colore 0x0000 = trasparente."""
    x0, y0, w, h = tim["rect"]
    cols = tim["clut"][pal * 16:pal * 16 + 16]
    px = bytearray()
    for i in tim["idx"]:
        c = cols[i] if i < len(cols) else 0
        px += bytes(((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31,
                     0 if c == 0 else 255))
    return w, h, px


# ---------------------------------------------------------------- geometria piu' morbida (normali + suddivisione)
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _norm(a):
    l = _dot(a, a) ** 0.5
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else (0.0, 1.0, 0.0)
def _key(p): return (round(p[0], 5), round(p[1], 5), round(p[2], 5))


def _smooth_normals(groups):
    """Normali per vertice mediate per area su tutte le facce che condividono la posizione.
    Il segno e' scelto in modo che puntino verso l'esterno rispetto al baricentro del modello."""
    acc, cen, n, test = {}, [0.0, 0.0, 0.0], 0, 0.0
    tris = []
    for g in groups.values():
        P = g["pos"]
        for i in range(0, len(P), 3):
            tris.append((P[i], P[i + 1], P[i + 2]))
            for q in tris[-1]:
                cen = [cen[0] + q[0], cen[1] + q[1], cen[2] + q[2]]; n += 1
    cen = tuple(c / max(n, 1) for c in cen)
    for a, b, c in tris:
        nr = _cross(_sub(b, a), _sub(c, a))                      # lunghezza = 2 x area
        fc = ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3)
        test += _dot(nr, _sub(fc, cen))
        for q in (a, b, c):
            t = acc.setdefault(_key(q), [0.0, 0.0, 0.0])
            t[0] += nr[0]; t[1] += nr[1]; t[2] += nr[2]
    # NON si inverte per puntare "verso l'esterno": con materiale a doppia faccia Godot inverte la normale sulle facce
    # viste da dietro in base al VERSO DEI TRIANGOLI, quindi la normale attributo deve seguire il winding (provato a vista:
    # invertirla per il baricentro colora tutto di azzurro e cancella la livrea).
    sign = 1.0
    return {k: _norm((sign * v[0], sign * v[1], sign * v[2])) for k, v in acc.items()}


def _refine(g, nmap, levels=0, alpha=0.5):
    """Restituisce (pos, uv, col, normali) di un gruppo, con `levels` suddivisioni (x4 triangoli ciascuna):
    punti medi spostati con la tessellazione di Phong (proiezione sui piani tangenti dei vertici)."""
    P, U, C = g["pos"], g["uv"], g["col"]
    T = []
    for i in range(0, len(P), 3):
        T.append([(P[i + k], U[i + k], C[i + k], nmap[_key(P[i + k])]) for k in range(3)])
    def mid(a, b):
        m = tuple((a[0][i] + b[0][i]) / 2 for i in range(3))
        pa = tuple(m[i] - _dot(_sub(m, a[0]), a[3]) * a[3][i] for i in range(3))
        pb = tuple(m[i] - _dot(_sub(m, b[0]), b[3]) * b[3][i] for i in range(3))
        pos = tuple((1 - alpha) * m[i] + alpha * (pa[i] + pb[i]) / 2 for i in range(3))
        uv = tuple((a[1][i] + b[1][i]) / 2 for i in range(2))
        col = tuple((a[2][i] + b[2][i]) / 2 for i in range(4))
        return (pos, uv, col, _norm(tuple(a[3][i] + b[3][i] for i in range(3))))
    for _ in range(levels):
        nt = []
        for a, b, c in T:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nt += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
        T = nt
    pos = [v[0] for t in T for v in t]; uv = [v[1] for t in T for v in t]
    col = [v[2] for t in T for v in t]; nor = [v[3] for t in T for v in t]
    return pos, uv, col, nor


def to_gltf(m, tim_bytes, outbase, scale=0.01, smooth=False, subdiv=0):
    """Scrive outbase.gltf (+ outbase_pN.png, una per palette usata). Facce non indicizzate
    (UV e colore per faccia); y invertita (PSX y verso il basso) con winding corretto."""
    tim = parse_tim4(tim_bytes)
    x0, y0, tw, th = tim["rect"]                   # px VRAM (x in px 4bpp)
    # primitiva = (pal) -> liste
    groups = {}
    def clut_pal(clut):  # clut = x/16 + y*64 ; x in 16-px unita'
        cx = (clut & 0x3F) * 16; cy = clut >> 6
        if cy != tim["clut_xy"][1]:
            raise ValueError("CLUT su altra riga: non gestito")
        return (cx - tim["clut_xy"][0]) // 16
    def add(face):
        verts, cols, uvs, clut, tpage = face
        pal = clut_pal(clut); px, py = (tpage & 15) * 64 * 4, ((tpage >> 4) & 1) * 256
        g = groups.setdefault(pal, {"pos": [], "uv": [], "col": []})
        tris = [(0, 1, 2)] if len(verts) == 3 else [(0, 1, 2), (2, 1, 3)]
        for a, b, c in tris:
            for k in (a, c, b):                    # y flip -> winding invertito
                x, y, z = m["verts"][verts[k]]
                g["pos"].append((x * scale, -y * scale, z * scale))
                u, v = uvs[k]
                g["uv"].append(((px + u - x0 + 0.5) / tw, (py + v - y0 + 0.5) / th))
                g["col"].append(tuple(min(255, c2 * 2) / 255 for c2 in cols[k]) + (1.0,))
    # UV/clut/tpage: rileggiamo dal blob dato che _prims non li espone -> usiamo m["raw"]
    for i, col, uv, clut, tpage in m["faces"]:
        add((i, col, uv, clut, tpage))
    nmap = _smooth_normals(groups) if (smooth or subdiv) else None
    buf = bytearray(); views = []; accs = []; prims = []; mats = []; texs = []; imgs = []
    def push(data, target, count, ctype, mn=None, mx=None, ctypeid=5126):
        while len(buf) % 4: buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(data), "target": 34962})
        buf.extend(data)
        a = {"bufferView": len(views) - 1, "componentType": ctypeid, "count": count, "type": ctype}
        if mn: a["min"], a["max"] = mn, mx
        accs.append(a); return len(accs) - 1
    for n, (pal, g) in enumerate(sorted(groups.items())):
        w, h, rgba = palette_image(tim, pal)
        png = f"{outbase}_p{pal}.png"; _png_rgba(png, w, h, rgba)
        imgs.append({"uri": os.path.basename(png)}); texs.append({"source": len(imgs) - 1, "sampler": 0})
        mats.append({"name": f"pal{pal}", "doubleSided": True, "alphaMode": "MASK", "alphaCutoff": 0.5,
                     "pbrMetallicRoughness": {"baseColorTexture": {"index": len(texs) - 1},
                                              "metallicFactor": 0.0, "roughnessFactor": 1.0}})
        P, UV, CO, NO = g["pos"], g["uv"], g["col"], None
        if nmap is not None:
            P, UV, CO, NO = _refine(g, nmap, subdiv)
        pa = push(b"".join(struct.pack("<3f", *p) for p in P), 34962, len(P), "VEC3",
                  [min(p[i] for p in P) for i in range(3)], [max(p[i] for p in P) for i in range(3)])
        ua = push(b"".join(struct.pack("<2f", *u) for u in UV), 34962, len(P), "VEC2")
        ca = push(b"".join(struct.pack("<4f", *c) for c in CO), 34962, len(P), "VEC4")
        attrs = {"POSITION": pa, "TEXCOORD_0": ua, "COLOR_0": ca}
        if NO is not None:
            attrs["NORMAL"] = push(b"".join(struct.pack("<3f", *q) for q in NO), 34962, len(P), "VEC3")
        prims.append({"attributes": attrs, "material": n})
    gl = {"asset": {"version": "2.0", "generator": "AC2Remake acemodel"},
          "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
          "meshes": [{"primitives": prims}], "materials": mats, "textures": texs, "images": imgs,
          "samplers": [{"magFilter": 9728, "minFilter": 9728, "wrapS": 33071, "wrapT": 33071}],
          "accessors": accs, "bufferViews": views,
          "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," +
                       base64.b64encode(bytes(buf)).decode()}]}
    with open(outbase + ".gltf", "w") as f:
        json.dump(gl, f)
    return outbase + ".gltf"


# ------------------------------------------------- glTF da una VRAM ricostruita (piu' TIM, piu' palette)
def vram_new():
    return [0] * (1024 * 512)


def vram_apply_tim(vram, t):
    """Scrive in `vram` (lista di 1024*512 u16) l'immagine e la CLUT di un TIM, alle coordinate del suo header."""
    fl = struct.unpack_from("<I", t, 4)[0]
    pos = 8
    blocks = []
    if fl & 8:
        l, x, y, w, h = struct.unpack_from("<IhhHH", t, pos); blocks.append((x, y, w, h, pos + 12)); pos += l
    l, x, y, w, h = struct.unpack_from("<IhhHH", t, pos); blocks.append((x, y, w, h, pos + 12))
    for x, y, w, h, d in blocks:
        for r in range(h):
            for c in range(w):
                if 0 <= x + c < 1024 and 0 <= y + r < 512 and d + (r * w + c) * 2 + 2 <= len(t):
                    vram[(y + r) * 1024 + x + c] = struct.unpack_from("<H", t, d + (r * w + c) * 2)[0]
    return blocks


def vram_page_image(vram, tpage, clut):
    """Immagine RGBA 256x256 della pagina `tpage` con la palette `clut` (modi 4 e 8 bit)."""
    px, py = (tpage & 15) * 64, ((tpage >> 4) & 1) * 256
    mode = (tpage >> 7) & 3
    cx, cy = (clut & 0x3F) * 16, clut >> 6
    pal = [vram[cy * 1024 + cx + i] if cx + i < 1024 else 0 for i in range(256 if mode == 1 else 16)]
    out = bytearray()
    for v in range(256):
        for u in range(256):
            if mode == 0:
                wd = vram[(py + v) * 1024 + (px + u // 4) % 1024]; i = (wd >> (4 * (u % 4))) & 15
            elif mode == 1:
                wd = vram[(py + v) * 1024 + (px + u // 2) % 1024]; i = (wd >> (8 * (u % 2))) & 255
            else:
                wd = vram[(py + v) * 1024 + (px + u) % 1024]; i = -1
            c = pal[i] if i >= 0 else wd
            out += bytes(((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31, 0 if c == 0 else 255))
    return bytes(out)


def to_gltf_vram(m, vram, outbase, scale=0.01, smooth=False, subdiv=0):
    """Come to_gltf, ma le texture si campionano dalla VRAM: una immagine per coppia (tpage, clut) usata."""
    groups = {}
    for verts, cols, uvs, clut, tpage in m["faces"]:
        g = groups.setdefault((tpage, clut), {"pos": [], "uv": [], "col": []})
        for a, b, c in ([(0, 1, 2)] if len(verts) == 3 else [(0, 1, 2), (2, 1, 3)]):
            for k in (a, c, b):
                x, y, z = m["verts"][verts[k]]
                g["pos"].append((x * scale, -y * scale, z * scale))
                u, v = uvs[k]
                g["uv"].append(((u + 0.5) / 256, (v + 0.5) / 256))
                g["col"].append(tuple(min(255, c2 * 2) / 255 for c2 in cols[k]) + (1.0,))
    nmap = _smooth_normals(groups) if (smooth or subdiv) else None
    buf = bytearray(); views = []; accs = []; prims = []; mats = []; texs = []; imgs = []
    def push(data, count, ctype, mn=None, mx=None):
        while len(buf) % 4: buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(data), "target": 34962})
        buf.extend(data)
        a = {"bufferView": len(views) - 1, "componentType": 5126, "count": count, "type": ctype}
        if mn: a["min"], a["max"] = mn, mx
        accs.append(a); return len(accs) - 1
    for n, ((tp, cl), g) in enumerate(sorted(groups.items())):
        png = f"{outbase}_t{tp:02x}_c{cl:04x}.png"
        _png_rgba(png, 256, 256, vram_page_image(vram, tp, cl))
        imgs.append({"uri": os.path.basename(png)}); texs.append({"source": len(imgs) - 1, "sampler": 0})
        mats.append({"name": f"tp{tp:02x}_cl{cl:04x}", "doubleSided": True, "alphaMode": "MASK", "alphaCutoff": 0.5,
                     "pbrMetallicRoughness": {"baseColorTexture": {"index": len(texs) - 1}, "metallicFactor": 0.0, "roughnessFactor": 1.0}})
        P, UV, CO, NO = g["pos"], g["uv"], g["col"], None
        if nmap is not None:
            P, UV, CO, NO = _refine(g, nmap, subdiv)
        pa = push(b"".join(struct.pack("<3f", *p) for p in P), len(P), "VEC3",
                  [min(p[i] for p in P) for i in range(3)], [max(p[i] for p in P) for i in range(3)])
        ua = push(b"".join(struct.pack("<2f", *u) for u in UV), len(P), "VEC2")
        ca = push(b"".join(struct.pack("<4f", *c) for c in CO), len(P), "VEC4")
        attrs = {"POSITION": pa, "TEXCOORD_0": ua, "COLOR_0": ca}
        if NO is not None:
            attrs["NORMAL"] = push(b"".join(struct.pack("<3f", *q) for q in NO), len(P), "VEC3")
        prims.append({"attributes": attrs, "material": n})
    gl = {"asset": {"version": "2.0", "generator": "AC2Remake acemodel/vram"}, "scene": 0, "scenes": [{"nodes": [0]}],
          "nodes": [{"mesh": 0}], "meshes": [{"primitives": prims}], "materials": mats, "textures": texs, "images": imgs,
          "samplers": [{"magFilter": 9728, "minFilter": 9728, "wrapS": 33071, "wrapT": 33071}],
          "accessors": accs, "bufferViews": views,
          "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(buf)).decode()}]}
    with open(outbase + ".gltf", "w") as f:
        json.dump(gl, f)
    return outbase + ".gltf"
