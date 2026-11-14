#!/usr/bin/env python3
"""ace2arc — archivio Ace Combat 2 (ACE2.DAT + ACE2.STH/ACE2.STP).

Specifica: psx-spx cdromfileformats.md, sezione "CDROM File Archive Ace Combat 2 and 3":

Directory (dentro ACE2.DAT per i dati, oppure il file ACE2.STH per lo streaming):
  000h u32 unknown (1)
  004h u32 numero entries N
  008h N × u64 entry:
         bit 0-27   size (DAT: size/4 → byte; STP: size/800h → byte)
         bit 28-31  type o canale (DAT ch0=data, ch2=exe; STP ch0-6 audio, ch8 video)
         bit 32-63  offset/800h nel file DAT o STP
"""
import os
import struct
import sys

BLOCK = 2048

# magics noti nel contenuto (sniff)
MAGICS = {
    b"\x10\x00\x00\x00": "TIM",
    b"\x41\x00\x00\x00": "TMD",
}


def parse_dir(data, kind):
    if len(data) < 8:
        raise ValueError("directory troppo corta")
    unk, n = struct.unpack_from("<II", data, 0)
    ents = []
    for i in range(n):
        e = struct.unpack_from("<Q", data, 8 + 8 * i)[0]
        size_raw = e & 0x0FFFFFFF
        chan = (e >> 28) & 0xF
        off_raw = (e >> 32) & 0xFFFFFFFF
        ents.append({
            "idx": i,
            "off": off_raw * BLOCK,
            "size": size_raw * (4 if kind == "DAT" else BLOCK),
            "chan": chan,
        })
    return unk, ents


def sniff(data):
    for magic, name in MAGICS.items():
        if data[:4] == magic:
            return name
    return "bin"


def extract(data, e, outdir, kind, prefix=None):
    blob = data[e["off"]:e["off"] + e["size"]]
    ext = sniff(blob).lower()
    name = prefix or f"entry{e['idx']:05d}_ch{e['chan']}"
    path = os.path.join(outdir, f"{name}.{ext}")
    os.makedirs(outdir, exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    return path, ext


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: ace2arc.py list DAT|STH FILE   |   ace2arc.py extract DAT|STH FILE IDX OUTDIR")
        sys.exit(2)
    cmd, kind, path = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    data = open(path, "rb").read()
    unk, ents = parse_dir(data, kind)
    if cmd == "list":
        print(f"unknown={unk} entries={len(ents)}")
        from collections import Counter
        by_ext = {}
        for e in ents:
            ext = sniff(data[e["off"]:e["off"] + 8])
            by_ext[ext] = by_ext.get(ext, 0) + 1
        for e in ents:
            head = data[e["off"]:e["off"] + 4].hex()
            print(f"[{e['idx']:5d}] ch={e['chan']} off={e['off']:10d} size={e['size']:9d} head={head}")
        print("riepilogo tipi:", dict(by_ext))
    elif cmd == "extract":
        idx, outdir = int(sys.argv[4]), sys.argv[5]
        path_out, ext = extract(data, ents[idx], outdir, kind)
        print(f"estratto → {path_out}")
    else:
        print(f"comando {cmd} non noto")
        sys.exit(2)
