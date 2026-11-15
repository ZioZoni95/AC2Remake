#!/usr/bin/env python3
"""ghidra_pick — estrae dal C decompilato (out/codice/overlay0.c) il testo grezzo di alcune funzioni (uso personale, output NON versionato).

  ghidra_pick.py [OUT.c] [FUN_xxxxxxxx ...]

Senza argomenti scrive out/codice_leggibile/musica_fighters_honor_grezzo.c con le funzioni che servono a ricostruire la logica musicale di
Fighter's Honor (SCOPERTE #38, #39). Da quel testo si riscrive a mano il C leggibile (out/codice_leggibile/musica_fighters_honor.c): nomi nostri,
commenti, struttura descritta in SCOPERTE #38-#39. Il C deriva dal codice di Namco: resta in out/, mai in git. Solo libreria standard.
"""
import os, re, sys

MUSICA = ["FUN_80047470", "FUN_80068fdc", "FUN_8006915c", "FUN_80069958", "FUN_800688d8", "FUN_80068200", "FUN_80068574",
          "FUN_8005e320", "FUN_8005e348", "FUN_800483d4", "FUN_800388ec"]


def main():
    a = sys.argv[1:]
    out = a.pop(0) if a and a[0].endswith(".c") else "out/codice_leggibile/musica_fighters_honor_grezzo.c"
    names = a or MUSICA
    src = open("out/codice/overlay0.c").read()
    blocks = {m.group(1): m.group(0).rstrip() for m in re.finditer(
        r"// ==== (FUN_[0-9a-f]+) @ [0-9a-f]+ size=\d+.*?(?=\n// ==== FUN_|\Z)", src, re.S)}
    miss = [n for n in names if n not in blocks]
    if miss:
        sys.exit("funzioni non trovate (hai eseguito ExportAll.java? docs/RECUPERO_ASSET.md §8): " + ", ".join(miss))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w").write("/* C grezzo di Ghidra: derivato dal codice di Namco, solo uso personale, NON versionare */\n\n" + "\n\n\n".join(blocks[n] for n in names) + "\n")
    print(f"{len(names)} funzioni -> {out}")


if __name__ == "__main__":
    main()
