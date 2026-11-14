#!/usr/bin/env python3
"""ac2_export_godot — scrive mission.json per il visualizzatore Godot dalla parte 2 della missione (uso personale).

  ac2_export_godot.py out/fighters_honor/parte2_tabelle.json OUT/mission.json

Tutte le unita' della T1 (lista iniziale, SCOPERTE #27) con posizione risolta dalla T2, categoria, squadra, tipo di modello;
il giocatore e' la T1[0]. Modello del tipo t = models/unita_{3t+2} (LOD0). Campi = ipotesi dove indicato nei documenti.
"""
import json, sys


def main(p2, out):
    t = json.load(open(p2))
    u = t["unita"]
    d = {"giocatore": {"pos": u[0]["pos"], "angoli": u[0]["angoli"]}, "unita": u[1:],
         "piazzamento_T2": [r["pos"] for r in t["tabelle"]["T2"]["record_dati"]],
         "nota": "pos in unita' di mondo; x,z orizzontali, y verso il basso (quota = -y); a_terra: quota 0 = appoggiata al suolo (altezza terreno non decodificata)"}
    json.dump(d, open(out, "w"), indent=1)
    print(f"{len(u)} unita' (giocatore incluso), {sum(1 for x in u if x['a_terra'])} a terra, {len(d['piazzamento_T2'])} punti T2 -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    main(*sys.argv[1:])
