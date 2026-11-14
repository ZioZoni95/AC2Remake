#!/usr/bin/env python3
"""ac2_mission — estrae il blocco dati di una missione di Ace Combat 2 (uso personale, output NON versionato).

  ac2_mission.py extract STADIO OUTDIR [VARIANTE]     STADIO 0..32 (0 Gambit ... 32 Fighter's Honor), VARIANTE 0..2 (default 1)

Produce in OUTDIR: parti grezze (partNN.bin), texture dei TIM (tex/*.png), VRAM ricostruita (vram.png),
modelli delle unita' texturizzati (models/*.gltf) e manifest.json con dimensioni, coordinate VRAM e conteggi.
Fatti (SCOPERTE #18, #19, #20): entry DAT = 78 + 3*posizione(stadio) + variante, dove la posizione salta gli
id 13, 17, 19; l'entry e' un contenitore [size][11][off x 11]; parti 8 e 9 = TIM, parte 1 = modelli a 3 LOD.
"""
import json, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ace2arc, acemodel, ac2_extract as X, pngout, tim2png  # noqa: E402

MISSING = (13, 17, 19)
# Parte 2 = definizione della missione (SCOPERTE #24): intestazione di 13 parole [flag, off1..off12], ogni offset punta a una
# tabella [contatore u32][record]; dimensioni di record ricavate dai dati (tutte intere) e confermate dal codice (FUN_80046394).
P2_RECORD = {1: 20, 2: 20, 3: 8, 4: 28, 5: 36, 6: 52, 7: 28, 8: 24, 9: 12}


def entry_for(stage, variant=1):
    pos = stage - sum(1 for m in MISSING if m < stage)
    return 78 + 3 * pos + variant


def split(b, hdr):
    n = struct.unpack_from("<I", b, hdr)[0]
    offs = list(struct.unpack_from("<%dI" % n, b, hdr + 4)) + [len(b)]
    return [b[offs[j]:offs[j + 1]] for j in range(n)]


def decode_part2(p):
    """Tabelle della parte 2 -> dict. Campi NON ancora interpretati restano come parole grezze (s32 e hex)."""
    w = struct.unpack_from("<13I", p, 0)
    offs = list(w[1:13])
    out = {"flag": hex(w[0]), "tabelle": {}}
    for t in range(1, 10):
        o = offs[t - 1]; n = struct.unpack_from("<I", p, o)[0]; rs = P2_RECORD[t]
        recs = []
        for r in range(n):
            ws = struct.unpack_from("<%di" % (rs // 4), p, o + 4 + r * rs)
            recs.append({"i": r, "s32": list(ws), "hex": [f"{x & 0xffffffff:08x}" for x in ws]})
        out["tabelle"][f"T{t}"] = {"offset": o, "record": n, "byte_per_record": rs, "record_dati": recs}
    out["tabelle"]["T10"] = {"offset": offs[9], "ascii": p[offs[9]:offs[9] + 76].split(b"\0")[0].decode("latin-1")}
    # T2 (verificata contro le unita' vive): parole 2,3,4 = x, y, z in unita' di mondo (le unita' vive li hanno x2048)
    for r in out["tabelle"]["T2"]["record_dati"]:
        r["pos"] = r["s32"][2:5]
    out["unita"] = decode_units(p, offs)
    return out


def decode_units(p, offs):
    """T1 = lista iniziale delle unita' (indice = slot del pool). Campi ricavati da FUN_80046dfc (SCOPERTE #27):
    short+0 = capo formazione; byte+8 = categoria (0 giocatore, 1/4/7 aerea->T4, 2/3/5/6/8/9 terrestre->T5);
    byte+9 = indice posizione in T2 (x,y,z a +8/+0xc/+0x10, angoli short a +2/+4/+6; y=0 => appoggiata al suolo);
    byte+0xb = tipo di modello (0xff = nessuno); byte+0xc = parametro (w2 dello slot); byte+0xd = squadra; byte+0xf = sottotipo."""
    def rec(t, rs, i):
        o = offs[t - 1]
        return p[o + 4 + i * rs:o + 4 + (i + 1) * rs]
    n1 = struct.unpack_from("<I", p, offs[0])[0]
    res = []
    for i in range(n1):
        r = rec(1, 20, i)
        t2 = rec(2, 20, r[9])
        x, y, z = struct.unpack_from("<3i", t2, 8)
        res.append({"slot": i, "capo": struct.unpack_from("<h", r, 0)[0], "categoria": r[8], "t2": r[9],
                    "pos": [x, y, z], "angoli": list(struct.unpack_from("<3h", t2, 2)), "a_terra": y == 0,
                    "tipo": (0 if r[11] == 0xff else r[11]), "tipo_grezzo": r[11], "param": r[12], "squadra": r[13],
                    "sottotipo": r[15], "hex": r.hex()})
    return res


def extract(stage, outdir, variant=1, dat="out/iso/ACE2.DAT"):
    e = entry_for(stage, variant)
    ents = X.read_dat(dat)
    with open(dat, "rb") as f:
        f.seek(ents[e]["off"]); b = f.read(ents[e]["size"])
    parts = split(b, 4)                      # [size][N][offs]: il conteggio sta a +4
    os.makedirs(os.path.join(outdir, "tex"), exist_ok=True); os.makedirs(os.path.join(outdir, "models"), exist_ok=True)
    man = {"stadio": stage, "variante": variant, "entry_dat": e, "dimensione": len(b), "parti": [], "texture": [], "modelli": []}
    vram = acemodel.vram_new()
    for j, p in enumerate(parts):
        open(os.path.join(outdir, f"part{j:02d}.bin"), "wb").write(p)
        man["parti"].append({"indice": j, "byte": len(p)})
    for pj in (8, 9):
        if len(parts) <= pj:
            continue
        for tag, t in X.walk(parts[pj], f"p{pj}"):
            blocks = acemodel.vram_apply_tim(vram, t)
            tim2png.to_png(t, os.path.join(outdir, "tex", tag + ".png"))
            man["texture"].append({"nome": tag, "blocchi_vram": [list(bk[:4]) for bk in blocks]})
    rows = []
    for y in range(512):
        r = bytearray()
        for x in range(1024):
            c = vram[y * 1024 + x]
            r += bytes(((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31))
        rows.append(bytes(r))
    pngout.write_png(os.path.join(outdir, "vram.png"), 1024, 512, rows)
    if len(parts) > 1:
        items = split(parts[1], 0)           # parte 1: [N][offs] senza size iniziale
        for j, s in enumerate(items):
            if len(s) < 16:
                continue
            try:
                m = acemodel.parse_geometry(s)
            except Exception:
                continue
            base = os.path.join(outdir, "models", f"unita_{j:02d}")
            acemodel.to_obj(m, base + ".obj")
            acemodel.to_gltf_vram(m, vram, base)
            man["modelli"].append({"elemento": j, "tipo": j // 3, "lod": j % 3, "vertici": len(m["verts"]),
                                   "gt3": len(m["tris"]), "gt4": len(m["quads"])})
    if len(parts) > 2:
        p2 = decode_part2(parts[2])
        json.dump(p2, open(os.path.join(outdir, "parte2_tabelle.json"), "w"), indent=1)
        man["parte2"] = {t: v.get("record") for t, v in p2["tabelle"].items()}
        # mappa dall'alto della T2: x orizzontale, z verticale, colore per quota (y: piu' negativo = piu' in alto)
        pts = [r["pos"] for r in p2["tabelle"]["T2"]["record_dati"]]
        xs = [q[0] for q in pts]; zs = [q[2] for q in pts]
        if pts:
            W = H = 600; m = 30
            sc = min((W - 2 * m) / max(max(xs) - min(xs), 1), (H - 2 * m) / max(max(zs) - min(zs), 1))
            img = [bytearray(b"\x18\x1c\x28" * W) for _ in range(H)]
            for x, y, z in pts:
                px = int(m + (x - min(xs)) * sc); py = int(m + (z - min(zs)) * sc)
                c = (240, 200, 60) if y > -2500 else (90, 170, 240)       # a terra / in quota
                for dy in range(-3, 4):
                    for dx in range(-3, 4):
                        if 0 <= px + dx < W and 0 <= py + dy < H: img[py + dy][(px + dx) * 3:(px + dx) * 3 + 3] = bytes(c)
            pngout.write_png(os.path.join(outdir, "mappa_t2.png"), W, H, [bytes(r) for r in img])
    json.dump(man, open(os.path.join(outdir, "manifest.json"), "w"), indent=1)
    print(f"stadio {stage} variante {variant}: entry {e} ({len(b)} B), {len(parts)} parti, "
          f"{len(man['texture'])} TIM, {len(man['modelli'])} modelli -> {outdir}")


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] != "extract":
        print(__doc__); sys.exit(2)
    extract(int(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1)
