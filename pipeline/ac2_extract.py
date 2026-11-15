#!/usr/bin/env python3
"""ac2_extract — estrazione in blocco dal disco di Ace Combat 2 (uso personale, output NON versionato).

  ac2_extract.py iso    DISCO.bin OUT      file ISO (tranne ACE2.STP, 407 MB) in OUT/
  ac2_extract.py tims   OUT/ACE2.DAT OUT   tutti i TIM validati (ricerca ricorsiva nei container) -> PNG
  ac2_extract.py models OUT/ACE2.DAT OUT   tutti i modelli (geometria + TIM) -> glTF texturizzato + PNG per palette
  ac2_extract.py all    OUT/ACE2.DAT OUT   TUTTE le 226 entry: ogni sotto-file grezzo + classificazione + manifest.json (copertura)

Un TIM e' accettato solo se la sua lunghezza dichiarata (CLUT + immagine) sta nel sotto-file
(altrimenti la ricerca ricorsiva da' migliaia di falsi positivi: SCOPERTE #7).
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acemodel, psxcd, tim2png  # noqa: E402


def read_dat(path):
    with open(path, "rb") as f:
        head = f.read(8)
        n = struct.unpack_from("<I", head, 4)[0]
        f.seek(0)
        d = f.read(8 + 8 * n)
    import ace2arc
    return ace2arc.parse_dir(d, "DAT")[1]


def tim_len(s):
    fl = struct.unpack_from("<I", s, 4)[0]
    pos = 8
    if fl & 8:
        pos += struct.unpack_from("<I", s, pos)[0]
    return pos + struct.unpack_from("<I", s, pos)[0]


def valid_tim(s):
    if len(s) < 20 or s[:4] != b"\x10\0\0\0" or s[5:8] != b"\0\0\0" or (s[4] & 7) > 3:
        return False
    try:
        n = tim_len(s)
    except struct.error:
        return False
    return n <= len(s) and len(s) - n < 2048


def containers(b, depth=0):
    """Rende (indice_percorso, sotto-file) se b e' un container [N][off..] o [size][N][off..]."""
    if len(b) < 12 or depth > 2:
        return
    w0, w1 = struct.unpack_from("<II", b, 0)
    n, tb = (w1, 8) if w0 == len(b) else (w0, 4)
    if not (0 < n < 64 and tb + 4 * n <= len(b)):
        return
    offs = list(struct.unpack_from("<%dI" % n, b, tb)) + [len(b)]
    if offs[0] < tb + 4 * n or any(offs[j] > offs[j + 1] for j in range(n)):
        return
    for j in range(n):
        yield j, b[offs[j]:offs[j + 1]]


def walk(b, tag, depth=0):
    for j, s in containers(b, depth) or ():
        if valid_tim(s):
            yield f"{tag}_{j}", s
        else:
            yield from walk(s, f"{tag}_{j}", depth + 1)


def entries(dat):
    ents = read_dat(dat)
    with open(dat, "rb") as f:
        for e in ents:
            f.seek(e["off"])
            b = f.read(e["size"])
            if b[:8] != b"PS-X EXE":
                yield e["idx"], b


def cmd_iso(disc, out):
    d = psxcd.Disc(disc)
    for p, e in psxcd.list_all(d):
        if p.upper().endswith("ACE2.STP"):
            print("salto", p, "(407 MB, streaming)"); continue
        print(psxcd.extract_file(d, e, out))


def cmd_tims(dat, out):
    os.makedirs(out, exist_ok=True)
    ok = bad = 0
    for idx, b in entries(dat):
        for tag, s in walk(b, "e%03d" % idx):
            try:
                tim2png.to_png(s, os.path.join(out, tag + ".png")); ok += 1
            except Exception as ex:
                bad += 1; print("errore", tag, ex)
    print(f"TIM convertiti: {ok}  errori: {bad}")


def cmd_models(dat, out):
    os.makedirs(out, exist_ok=True)
    ok = bad = 0
    for idx, b in entries(dat):
        for j, s in containers(b) or ():
            parts = [p for _, p in containers(s) or ()]
            if len(parts) == 3 and parts[2][:4] == b"\x10\0\0\0":
                try:
                    m = acemodel.parse_geometry(parts[1])
                    acemodel.to_gltf(m, parts[2], os.path.join(out, "e%03d_%d" % (idx, j)))
                    ok += 1
                except Exception as ex:
                    bad += 1; print("salto e%03d_%d: %s" % (idx, j, ex))
    print(f"modelli esportati: {ok}  saltati: {bad}")


MAGIC = {b"pBAV": "banco_suoni_VAB", b"VAGp": "campione_VAG", b"pQES": "sequenza_SEQ", b"SShd": "SShd", b"STR\x00": "STR"}


def classify(s):
    """Tipo riconosciuto di un sotto-file (le etichette con ? sono ipotesi da euristica)."""
    if s[:8] == b"PS-X EXE":
        return "eseguibile_PSX"
    if valid_tim(s):
        return "TIM"
    if len(s) >= 16 and struct.unpack_from("<H", s, 6)[0] == 0x5907:
        return "tessera_terreno"
    for m, k in MAGIC.items():
        if s[:4] == m:
            return k
    if len(s) >= 16 and sum(1 for c in s[:256] if 32 <= c < 127 or c in (9, 10, 13)) >= 0.9 * min(len(s), 256):
        return "testo?"
    return "dati"


def leaves(b, tag, depth=0):
    """Scende nei container annidati: rende (percorso, bytes) delle foglie e dei container stessi come nodo."""
    subs = list(containers(b, 0) or ()) if depth < 6 and not valid_tim(b) and b[:8] != b"PS-X EXE" else []
    if subs:
        for j, s in subs:
            yield from leaves(s, f"{tag}/{j}", depth + 1)
    else:
        yield tag, b


def cmd_all(dat, out):
    import json, collections
    os.makedirs(out, exist_ok=True)
    ents = read_dat(dat)
    manifest, cnt, size = [], collections.Counter(), collections.Counter()
    with open(dat, "rb") as f:
        for e in ents:
            f.seek(e["off"]); b = f.read(e["size"])
            rows = []
            for path, s in leaves(b, "e%03d" % e["idx"]):
                k = classify(s)
                d = os.path.join(out, "e%03d" % e["idx"]); os.makedirs(d, exist_ok=True)
                fn = path.replace("/", "_") + ".bin"
                open(os.path.join(d, fn), "wb").write(s)
                rows.append({"percorso": path, "file": "e%03d/%s" % (e["idx"], fn), "byte": len(s), "tipo": k, "testa": s[:8].hex()})
                cnt[k] += 1; size[k] += len(s)
            manifest.append({"entry": e["idx"], "offset": e["off"], "byte": e["size"], "foglie": rows})
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    tot = sum(size.values())
    print(f"{len(ents)} entry, {sum(cnt.values())} sotto-file, {tot // 1024} KB salvati in {out}")
    for k in sorted(size, key=lambda x: -size[x]):
        print(f"  {k:20s} {cnt[k]:6d} file {size[k] // 1024:8d} KB  ({100 * size[k] / tot:.1f}%)")


if __name__ == "__main__":
    cmds = {"iso": cmd_iso, "tims": cmd_tims, "models": cmd_models, "all": cmd_all}
    if len(sys.argv) != 4 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(2)
    cmds[sys.argv[1]](sys.argv[2], sys.argv[3])
