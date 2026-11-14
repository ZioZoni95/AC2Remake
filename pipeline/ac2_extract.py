#!/usr/bin/env python3
"""ac2_extract — estrazione in blocco dal disco di Ace Combat 2 (uso personale, output NON versionato).

  ac2_extract.py iso    DISCO.bin OUT      file ISO (tranne ACE2.STP, 407 MB) in OUT/
  ac2_extract.py tims   OUT/ACE2.DAT OUT   tutti i TIM validati (ricerca ricorsiva nei container) -> PNG
  ac2_extract.py models OUT/ACE2.DAT OUT   tutti i modelli (geometria + TIM) -> glTF texturizzato + PNG per palette

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


if __name__ == "__main__":
    cmds = {"iso": cmd_iso, "tims": cmd_tims, "models": cmd_models}
    if len(sys.argv) != 4 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(2)
    cmds[sys.argv[1]](sys.argv[2], sys.argv[3])
