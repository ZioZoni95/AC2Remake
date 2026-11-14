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


def entry_for(stage, variant=1):
    pos = stage - sum(1 for m in MISSING if m < stage)
    return 78 + 3 * pos + variant


def split(b, hdr):
    n = struct.unpack_from("<I", b, hdr)[0]
    offs = list(struct.unpack_from("<%dI" % n, b, hdr + 4)) + [len(b)]
    return [b[offs[j]:offs[j + 1]] for j in range(n)]


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
    json.dump(man, open(os.path.join(outdir, "manifest.json"), "w"), indent=1)
    print(f"stadio {stage} variante {variant}: entry {e} ({len(b)} B), {len(parts)} parti, "
          f"{len(man['texture'])} TIM, {len(man['modelli'])} modelli -> {outdir}")


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] != "extract":
        print(__doc__); sys.exit(2)
    extract(int(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1)
