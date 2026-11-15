#!/usr/bin/env python3
"""ghidra_split_mission — ricava dal codice decompilato dell'overlay 0 le funzioni del MODULO MISSIONE (uso personale, output NON versionato).

  ghidra_split_mission.py [out/codice]

Legge SOLO out/codice/overlay0.c (prodotto da ExportAll.java, docs/GUIDA.md §4: l'intestazione di ogni funzione elenca i chiamati) e scrive
  out/codice/missione_funzioni.json   nomi delle funzioni del modulo missione
  out/codice/missione_completa.c      il loro C decompilato, in ordine di indirizzo
Regola (ricostruita il 2026-11-15, 513 funzioni, 327.768 byte): funzioni raggiungibili dal dispatcher dei moduli FUN_8002a0e4
meno il dispatcher stesso e due funzioni condivise con gli altri moduli (FUN_80063100, FUN_80069244).
Solo libreria standard. Il C e' derivato dal codice di Namco: resta in out/, mai in git.
"""
import json, os, re, sys

ROOT, EXCL = "FUN_8002a0e4", {"FUN_8002a0e4", "FUN_80063100", "FUN_80069244"}


def main(d):
    src = open(os.path.join(d, "overlay0.c")).read()
    g = {}
    for m in re.finditer(r"// ==== (FUN_[0-9a-f]+) @ [0-9a-f]+ size=(\d+) chiamanti=\[([^\]]*)\] chiama=\[([^\]]*)\]", src):
        g[m.group(1)] = {"size": int(m.group(2)), "callees": [x for x in m.group(4).split(",") if x]}
    seen, st = set(), [ROOT]
    while st:
        f = st.pop()
        if f in seen or f not in g:
            continue
        seen.add(f); st += g[f]["callees"]
    names = sorted(seen - EXCL, key=lambda f: int(f[4:], 16))
    blocks = {m.group(1): m.group(0) for m in re.finditer(r"// ==== (FUN_[0-9a-f]+) @ [0-9a-f]+ size=\d+.*?(?=\n// ==== FUN_|\Z)", src, re.S)}
    out = []
    for n in names:
        b = blocks[n]
        b = re.sub(r"^(// ==== FUN_[0-9a-f]+ @ [0-9a-f]+ size=\d+).*", r"\1", b, count=1)   # header senza elenco chiamanti
        out.append(b.rstrip("\n"))
    json.dump(names, open(os.path.join(d, "missione_funzioni.json"), "w"))
    open(os.path.join(d, "missione_completa.c"), "w").write("\n\n\n".join(out) + "\n")
    print(f"{len(names)} funzioni, {sum(g[n]['size'] for n in names)} byte -> {d}/missione_completa.c")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out/codice")
