#!/usr/bin/env python3
"""tmd2gltf — TMD (PSX) → OBJ + glTF 2.0.

Formato TMD (Sony Filefrmt, sez. 3D):
  u32 id=0x41, u32 flags (0 = fixed point), u32 nobjects
  oggetto (28 byte): u32 vertTop, vertCount, normTop, normCount,
                     primTop, primCount, s32 scale (16.16)
  vertice/normale: 3×s16 + u16 pad
  primitiva: u32 flag: bit30-31 mode (0=tri,1=quad), bit27-29 rate, bit24-26 mode2
  CALIBRAZIONE: i layout "rate" e la posizione dei bit vanno confermati sui
  file reali di AC2 (il fixture dei test usa rate=0, triangolo flat). Se un
  indice esce dal range, l'oggetto viene scartato con warning, non crash.
"""
import base64
import json
import os
import struct
import sys

# rate → (n_vertici, n_normali) — da calibrare sui file reali
RATE = {0: (3, 1), 1: (3, 3), 2: (4, 1), 3: (4, 4)}


def parse(data):
    if struct.unpack_from("<I", data, 0)[0] != 0x41:
        raise ValueError("non e' un TMD (id 0x41 mancante)")
    _flags, nobj = struct.unpack_from("<II", data, 4)
    objects = []
    pos = 12
    for _ in range(nobj):
        vt, vc, nt, nc, pt, pc, scale = struct.unpack_from("<7I", data, pos)
        pos += 28
        verts = []
        for i in range(vc):
            x, y, z, _pad = struct.unpack_from("<4h", data, vt + i * 8)
            s = scale / 65536.0 if scale else 1.0
            verts.append((x * s, y * s, z * s))
        norms = []
        for i in range(nc):
            x, y, z, _pad = struct.unpack_from("<4h", data, nt + i * 8)
            norms.append((x / 4096.0, y / 4096.0, z / 4096.0))
        tris = []
        cursor = pt
        ok = True
        for _ in range(pc):
            if cursor + 4 > len(data):
                ok = False
                break
            flag = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            mode = (flag >> 30) & 3
            rate = (flag >> 27) & 7
            mode2 = (flag >> 24) & 7
            if mode not in (0, 1) or rate not in RATE:
                ok = False
                break
            nv, nn = RATE[rate]
            textured = mode2 in (1, 3)
            gouraud = nn > 1
            idx = []
            for _v in range(nv):
                if cursor + 4 > len(data):
                    ok = False
                    break
                vid = struct.unpack_from("<I", data, cursor)[0]
                cursor += 4
                if vid >= vc:
                    ok = False
                    break
                idx.append(vid)
                if textured:
                    cursor += 4          # u16 u, u16 v
                if gouraud:
                    cursor += 4          # normale per vertice
                    if textured:
                        cursor += 4      # colore per vertice
            if not ok:
                break
            if nn == 1:                  # flat: una normale dopo i vertici
                cursor += 4
                cursor += 4              # colore (o CLUT id se textured)
            if mode == 0:
                tris.append((idx[0], idx[1], idx[2]))
            else:
                tris.append((idx[0], idx[1], idx[2]))
                tris.append((idx[0], idx[2], idx[3]))
        if ok:
            objects.append(dict(verts=verts, norms=norms, tris=tris))
        else:
            print("[tmd2gltf] oggetto: layout primitiva non riconosciuto, "
                  "scartato (CALIBRARE su file reali)", file=sys.stderr)
    return objects


def to_obj(objects, out):
    with open(out, "w") as f:
        base = 1
        for oi, o in enumerate(objects):
            f.write(f"# oggetto {oi}\n")
            for x, y, z in o["verts"]:
                f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            for a, b, c in o["tris"]:
                f.write(f"f {base + a} {base + b} {base + c}\n")
            base += len(o["verts"])


def to_gltf(objects, out):
    positions = bytearray()
    indices = bytearray()
    voff = 0
    for o in objects:
        for x, y, z in o["verts"]:
            positions += struct.pack("<fff", x, y, z)
        for a, b, c in o["tris"]:
            indices += struct.pack("<III", voff + a, voff + b, voff + c)
        voff += len(o["verts"])
    buf = bytes(positions) + bytes(indices)
    b64 = base64.b64encode(buf).decode()
    doc = {
        "asset": {"version": "2.0", "generator": "tmd2gltf (AC2Remake)"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "mode": 4}]}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions), "target": 34962},
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices),
             "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": voff, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5125, "count": len(indices) // 4,
             "type": "SCALAR"},
        ],
        "buffers": [{"uri": f"data:application/octet-stream;base64,{b64}"}],
    }
    with open(out, "w") as f:
        json.dump(doc, f)


if __name__ == "__main__":
    src = sys.argv[1]
    stem = os.path.splitext(src)[0]
    objects = parse(open(src, "rb").read())
    print(f"{len(objects)} oggetti")
    to_obj(objects, stem + ".obj")
    to_gltf(objects, stem + ".gltf")
