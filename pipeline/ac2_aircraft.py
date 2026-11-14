#!/usr/bin/env python3
"""ac2_aircraft — esporta gli aerei giocabili di Ace Combat 2 (uso personale, output NON versionato).

  ac2_aircraft.py list                          elenca i 24 aerei (id, nome, entry DAT)
  ac2_aircraft.py export NOME|ID OUTDIR [--smooth] [--subdiv N]   glTF texturizzato + OBJ (es. XFA-27, 23);
                                                (--smooth: normali morbide; --subdiv N: N livelli di suddivisione, file *_smoothN)
  ac2_aircraft.py all OUTDIR                    tutti e 24

Fatti (SCOPERTE #21, #22): i nomi sono nella tabella a 0x800af758 dell'overlay (id 0..23 = i giocabili);
entry DAT = 30 + id; ogni entry ha un modello [header 8 B][vertici][primitive] seguito dal suo TIM 4bpp
(la coda dopo le primitive). Richiede out/overlay0.bin e out/iso/ACE2.DAT (vedi docs/GUIDA.md).
"""
import os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ace2arc, acemodel  # noqa: E402

BASE = 0x80018000
TABLE = 0x800af758
N = 24


def names(overlay="out/overlay0.bin"):
    b = open(overlay, "rb").read()
    out = []
    for i in range(N):
        p = struct.unpack_from("<I", b, TABLE - BASE + 4 * i)[0]
        o = p - BASE
        out.append(b[o:b.index(b"\0", o)].decode())
    return out


def load_entry(dat, idx):
    d = open(dat, "rb")
    n = struct.unpack_from("<I", d.read(8), 4)[0]
    d.seek(0)
    ents = ace2arc.parse_dir(d.read(8 + 8 * n), "DAT")[1]
    d.seek(ents[idx]["off"])
    return d.read(ents[idx]["size"])


def find_model(b):
    """Primo modello plausibile (>=20 vertici, >=20 primitive, indici in range) con dati in coda."""
    for o in range(0, len(b) - 32, 4):
        po = struct.unpack_from("<H", b, o + 6)[0]
        if po < 16 or po > 0x2000 or (po - 8) % 8 or o + po > len(b):
            continue
        nv = (po - 8) // 8
        if nv < 20 or nv > 400:
            continue
        faces = []
        tris, quads, tail = acemodel._prims(b[o:], po, faces)
        if len(tris) + len(quads) < 20:
            continue
        mx = max([max(t[0]) for t in tris] + [max(q[0]) for q in quads] + [0])
        if mx < nv:
            g = b[o:]
            m = {"verts": [struct.unpack_from("<3h", g, 8 + 8 * i) for i in range(nv)],
                 "tris": tris, "quads": quads, "faces": faces, "tail": tail}
            return m, b[len(b) - tail:] if tail else b""
    return None, b""


def export(ident, outdir, dat="out/iso/ACE2.DAT", smooth=False, subdiv=0, suffix=""):
    nm = names()
    idx = int(ident) if str(ident).isdigit() else [x.lower() for x in nm].index(str(ident).lower())
    b = load_entry(dat, 30 + idx)
    m, tim = find_model(b)
    if m is None:
        raise SystemExit(f"{nm[idx]}: modello non trovato")
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, re.sub(r"[^A-Za-z0-9]+", "", nm[idx]).lower() + suffix)
    acemodel.to_obj(m, base + ".obj")
    try:
        acemodel.to_gltf(m, tim, base, smooth=smooth, subdiv=subdiv)
        tex = "con texture"
    except Exception as e:                      # TIM assente o CLUT su altra riga: solo geometria
        tex = f"SENZA texture ({e})"
    print(f"{idx:2} {nm[idx]:8} entry {30 + idx}  {len(m['verts'])} vert, {len(m['tris'])} GT3, {len(m['quads'])} GT4  {tex}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["list"]:
        for i, n in enumerate(names()):
            print(f"{i:2} {n:8} entry {30 + i}")
    elif a[:1] == ["export"] and len(a) >= 3:
        sd = int(a[a.index("--subdiv") + 1]) if "--subdiv" in a else 0
        sm = "--smooth" in a or sd > 0
        export(a[1], a[2], smooth=sm, subdiv=sd, suffix=(f"_smooth{sd}" if sm else ""))
    elif a[:1] == ["all"] and len(a) == 2:
        for i in range(N):
            export(i, a[1])
    else:
        print(__doc__)
