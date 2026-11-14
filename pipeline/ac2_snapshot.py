#!/usr/bin/env python3
"""ac2_snapshot — analizza uno snapshot di RAM/VRAM di una missione in corso (uso personale, output NON versionato).

  ac2_snapshot.py DIR_SNAPSHOT OUTDIR      DIR_SNAPSHOT contiene ram.bin (2 MB da 0x80000000) e vram.bin (1024x512x16 bit)

Produce in OUTDIR: objects.json (giocatore + 63 slot del pool con parole grezze e posizioni), mappa_unita.png (vista dall'alto),
vram.png. Come si fa lo snapshot: docs/GUIDA.md (canale remoto, comando di dump). Struttura (SCOPERTE #20, #21, #24):
pool a [0x800b8748] = 63 slot da 0x174 B; coordinate s32 con 11 bit frazionari alle parole 9..11 dello slot (+0x24/+0x28/+0x2c);
giocatore a 0x800bc5a0 (x, y, z, poi angoli). I nomi dei campi sono IPOTESI finche' non provati (vedi SCOPERTE).
"""
import json, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pngout  # noqa: E402

BASE = 0x80000000
SLOT = 0x174


def load(d):
    return open(os.path.join(d, "ram.bin"), "rb").read(), open(os.path.join(d, "vram.bin"), "rb").read()


def main(snap, out):
    R, V = load(snap)
    u32 = lambda a: struct.unpack_from("<I", R, a - BASE)[0]
    s32 = lambda a: struct.unpack_from("<i", R, a - BASE)[0]
    pool = u32(0x800b8748)
    objs = []
    for k in range(63):
        a = pool + k * SLOT
        w = [u32(a + 4 * i) for i in range(SLOT // 4)]
        objs.append({"slot": k, "indirizzo": hex(a), "flag_w0": hex(w[0]), "w1": w[1], "w2": w[2], "w3": hex(w[3]),
                     "w6": hex(w[6]),
                     "pos": [s32(a + 0x24) / 2048, s32(a + 0x28) / 2048, s32(a + 0x2c) / 2048],
                     "parole": [hex(x) for x in w[:24]]})
        o = objs[-1]
        p3 = o["pos"]
        o["valida"] = w[0] != 0 and all(abs(c) < 400000 for c in p3)
        # segnaposto "parcheggiati": stessa posizione fissa in attesa di essere usati (rinforzi?) - ipotesi
        o["parcheggiata"] = o["valida"] and abs(p3[0] + 47100) < 1 and abs(p3[1] + 8500) < 1 and abs(p3[2] - 80000) < 1
        o["attivo"] = o["valida"] and not o["parcheggiata"]
    pl = 0x800bc5a0
    player = {"indirizzo": hex(pl), "pos": [s32(pl) / 2048, s32(pl + 4) / 2048, s32(pl + 8) / 2048],
              "angoli": [s32(pl + 0x10), s32(pl + 0x14), s32(pl + 0x18)]}
    os.makedirs(out, exist_ok=True)
    json.dump({"giocatore": player, "unita": objs, "pool": hex(pool)}, open(os.path.join(out, "objects.json"), "w"), indent=1)
    # mappa dall'alto: asse x orizzontale, asse z verticale (z cresce verso il basso)
    pts = [(o["pos"][0], o["pos"][2], o["w2"]) for o in objs if o["attivo"]] + [(player["pos"][0], player["pos"][2], -1)]
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    W = H = 700; m = 40
    sx = (W - 2 * m) / max(max(xs) - min(xs), 1); sz = (H - 2 * m) / max(max(zs) - min(zs), 1); sc = min(sx, sz)
    img = [bytearray(b"\x18\x1c\x28" * W) for _ in range(H)]
    pal = [(230, 80, 80), (80, 200, 90), (90, 150, 240), (240, 200, 60), (200, 110, 230), (80, 220, 220), (240, 140, 60), (170, 170, 170)]
    def dot(x, y, c, r=4):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if 0 <= x + dx < W and 0 <= y + dy < H: img[y + dy][(x + dx) * 3:(x + dx) * 3 + 3] = bytes(c)
    for x, z, t in pts:
        px = int(m + (x - min(xs)) * sc); py = int(m + (z - min(zs)) * sc)
        dot(px, py, (255, 255, 255) if t == -1 else pal[t % len(pal)], 7 if t == -1 else 4)
    pngout.write_png(os.path.join(out, "mappa_unita.png"), W, H, [bytes(r) for r in img])
    rows = []
    for y in range(512):
        r = bytearray()
        for x in range(1024):
            c = struct.unpack_from("<H", V, (y * 1024 + x) * 2)[0]
            r += bytes(((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31))
        rows.append(bytes(r))
    pngout.write_png(os.path.join(out, "vram.png"), 1024, 512, rows)
    print(f"slot validi {sum(1 for o in objs if o['valida'])}/63: in scena {sum(1 for o in objs if o['attivo'])}, "
          f"parcheggiati {sum(1 for o in objs if o['parcheggiata'])}, non validi {sum(1 for o in objs if not o['valida'])}; "
          f"giocatore a {[round(v) for v in player['pos']]} -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    main(sys.argv[1], sys.argv[2])
