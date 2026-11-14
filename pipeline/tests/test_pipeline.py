#!/usr/bin/env python3
"""Test della pipeline con fixture sintetiche (nessun disco reale richiesto).

Genera in /tmp/opencode/fixture:
  - immagine CD raw 2352 con ISO9660 (PVD, dir, TEST.TXT, TEST.TIM, MODEL.TMD)
    e un file AUDIO.XA su settori MODE2/FORM2
  - verifica list/extract ISO, decode TIM→pixel attesi, parse TMD→triangolo,
    carving XA→campioni deterministici, parsing directory ACE2.
"""
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psxcd            # noqa: E402
import acemodel         # noqa: E402
import tim2png          # noqa: E402
import tmd2gltf         # noqa: E402
import xa_audio         # noqa: E402
import ace2arc          # noqa: E402

FIX = "/tmp/opencode/fixture"
RAW = 2352
SYNC = b"\x00" + b"\xff" * 10 + b"\x00"


def bcd(v):
    return ((v // 10) << 4) | (v % 10)


def msf(lba):
    t = lba + 150
    return bcd(t // 75 // 60), bcd((t // 75) % 60), bcd(t % 75)


def mode1_sector(lba, data2048):
    m, s, f = msf(lba)
    return (SYNC + bytes([m, s, f, 1]) + data2048 +
            b"\x00" * (RAW - 16 - len(data2048)))          # EDC+ECC (288 per 2048)


def mode2_sector(lba, sub, payload):
    assert len(payload) == 2324
    m, s, f = msf(lba)
    return (SYNC + bytes([m, s, f, 2]) + sub + payload +
            b"\x00" * (RAW - 24 - len(payload)))           # EDC (4)


def dir_record(name, lba, size, is_dir=False):
    nm = name.encode() if is_dir else (name + ";1").encode()
    rec = bytearray(33 + len(nm) + (1 - (33 + len(nm)) % 2))
    rec[0] = len(rec)
    struct.pack_into("<I", rec, 2, lba)
    struct.pack_into(">I", rec, 6, lba)
    struct.pack_into("<I", rec, 10, size)
    struct.pack_into(">I", rec, 14, size)
    rec[25] = 2 if is_dir else 0
    struct.pack_into("<H", rec, 28, 1)
    rec[32] = len(nm)
    rec[33:33 + len(nm)] = nm
    return bytes(rec)


def build_image():
    # fixture TIM 16bpp 2x2: rosso, verde, blu, bianco
    colors = [0x7C00, 0x03E0, 0x001F, 0x7FFF]
    tim = struct.pack("<II", 0x10, 0x02)          # 16bpp, no CLUT
    tim += struct.pack("<IhhHH", 12 + 8, 0, 0, 2, 2)
    tim += b"".join(struct.pack("<H", c) for c in colors)

    # fixture TMD: 1 oggetto, 3 vertici, 1 triangolo flat (rate 0)
    verts = b"".join(struct.pack("<4h", v[0], v[1], v[2], 0) for v in
                     [(0, 0, 0), (16384, 0, 0), (0, 16384, 0)])
    norms = b"".join(struct.pack("<4h", 0, 0, 4096, 0) for _ in range(3))
    prim_flag = 0x00000000                        # tri, rate0 (3V1N), mode2=0 flat nontex
    prim = struct.pack("<5I", prim_flag, 0, 1, 2, 0) + struct.pack("<I", 0x808080)
    tmd = struct.pack("<III", 0x41, 0, 1)
    off_v, off_n, off_p = 12 + 28, 12 + 28 + 24, 12 + 28 + 24 + 24
    tmd += struct.pack("<7I", off_v, 3, off_n, 3, off_p, 1, 0x10000)
    tmd += verts + norms + prim
    assert len(tmd) == off_p + len(prim)

    txt = b"hello ace combat\n"
    xa_payload = bytes([0x00] * 4 + [0x00] * 4 + [0x00] * 8 +
                       [0x04] * 112) + b"\x00" * (2324 - 128)
    # porzione: header 0..3 copia, 4..7 shift/filtro (0), 8..11 copia; dati 0x04
    xa_payload = bytearray(xa_payload)
    xa_payload[4:8] = b"\x00\x00\x00\x00"
    xa_payload[0:4] = b"\x00\x00\x00\x00"
    xa_payload[8:16] = b"\x00" * 8
    for i in range(18):                            # 18 porzioni identiche
        # header ADPCM: filtri=1 (f0=60), shift=12 (stored 0) per tutti i blocchi nib0
        hdr = b"\x10\x00\x10\x00"
        xa_payload[i * 128:i * 128 + 4] = hdr      # copia di 4..7
        xa_payload[i * 128 + 4:i * 128 + 8] = hdr  # shift/filtro dei 4 blocchi
        xa_payload[i * 128 + 8:i * 128 + 12] = hdr  # copia
        xa_payload[i * 128 + 12:i * 128 + 16] = bytes(4)
        xa_payload[i * 128 + 16:i * 128 + 128] = b"\x04" * 112

    files = [("TEST.TXT", txt, "data"), ("TEST.TIM", tim, "data"),
             ("MODEL.TMD", tmd, "data")]
    # layout: LBA16 PVD, LBA17 dir, 18.. txt, tim, tmd, 21..23 XA
    lba_map = {}
    nxt = 18
    for name, content, _ in files:
        lba_map[name] = nxt
        nxt += (len(content) + 2047) // 2048
    xa_lba = nxt
    xa_nsect = 3
    dir_data = b"".join(dir_record(n, lba_map[n], len(c)) for n, c, _ in files)
    dir_data += b"\x00" * (-len(dir_data) % 2048)

    pvd = bytearray(2048)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[6] = 1
    struct.pack_into("<I", pvd, 80, 80)            # volume size (finto ma valido)
    pvd[156:156 + 34] = dir_record("", 17, 2048, is_dir=True)

    sect = [mode1_sector(i, b"\x00" * 2048) for i in range(40)]  # tutti i settori con sync
    sect[16] = mode1_sector(16, bytes(pvd))
    sect[17] = mode1_sector(17, dir_data)
    for name, content, _ in files:
        padded = content + b"\x00" * (-len(content) % 2048)
        for i in range(0, len(padded), 2048):
            sect[lba_map[name] + i // 2048] = mode1_sector(lba_map[name] + i // 2048, padded[i:i + 2048])
    sub = bytes([1, 1, 0x04 | 0x20 | 0x40, 0x00, 0, 0, 0, 0])  # audio, form2, RT, coding mono 37800
    for i in range(xa_nsect):
        sect[xa_lba + i] = mode2_sector(xa_lba + i, sub, bytes(xa_payload))

    os.makedirs(FIX, exist_ok=True)
    img = os.path.join(FIX, "test.bin")
    with open(img, "wb") as f:
        f.write(b"".join(sect))
    return img, tim, tmd, xa_payload, xa_nsect, colors


def main():
    img, tim_bytes, tmd_bytes, xa_payload, xa_nsect, colors = build_image()
    ok = []

    def check(name, cond):
        ok.append((name, bool(cond)))
        print(("PASS " if cond else "FAIL ") + name)

    disc = psxcd.Disc(img)
    files = psxcd.list_all(disc, path="")
    names = [p for p, _ in files]
    check("iso: 3 file trovati", names == ["TEST.TXT", "TEST.TIM", "MODEL.TMD"])

    out = os.path.join(FIX, "out")
    dest = psxcd.extract_file(disc, dict(files)["TEST.TXT"], out)
    check("iso: TEST.TXT contenuto", open(dest, "rb").read() == b"hello ace combat\n")

    tim_data = open(psxcd.extract_file(disc, dict(files)["TEST.TIM"], out), "rb").read()
    w, h, rows = tim2png.decode(tim_data)
    expect = [tuple(((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31))
              for c in colors]
    got = [tuple(rows[r][c * 3:c * 3 + 3]) for r in range(h) for c in range(w)]
    check("tim: pixel attesi", got == expect)
    p = os.path.join(out, "TEST.TIM.png")
    tim2png.to_png(tim_data, p)
    check("tim: png scritto", os.path.exists(p) and os.path.getsize(p) > 60)

    # 4bpp+CLUT: 2 pixel per byte, nibble basso = pixel sinistro (regressione c//4 → c//2)
    clut = struct.pack("<IhhHH", 12 + 2 * 16, 0, 0, 16, 1) + b"".join(
        struct.pack("<H", i << 5) for i in range(16))        # indice i → verde i
    img4 = struct.pack("<IhhHH", 12 + 4, 0, 0, 1, 2) + bytes([0x21, 0x43, 0x65, 0x87])
    t4 = struct.pack("<II", 0x10, 8) + clut + img4
    w4, h4, rows4 = tim2png.decode(t4)
    idx4 = [round(rows4[r][c * 3 + 1] * 31 / 255) for r in range(h4) for c in range(w4)]
    check("tim: 4bpp ordine nibble", (w4, h4) == (4, 2) and idx4 == [1, 2, 3, 4, 5, 6, 7, 8])

    # acemodel: 4 vertici (header 8 B con offset primitive), 1 GT3 + 1 GT4
    vs = b"".join(struct.pack("<4h", x, y, z, 0) for x, y, z in [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)])
    gt3 = bytes([0, 1, 2, 0]) + bytes([9, 9, 9, 0x34]) * 3 + bytes([0, 0, 1, 0, 8, 0, 2, 0, 8, 8, 0, 0])
    gt4 = bytes([0, 1, 2, 3]) + bytes([9, 9, 9, 0x3C]) * 4 + bytes([0, 0, 1, 0, 8, 0, 2, 0, 0, 8, 0, 0, 8, 8, 0, 0])
    geo = struct.pack("<IHH", 0, 0, 8 + len(vs)) + vs + gt3 + gt4
    m = acemodel.parse_geometry(geo)
    check("acemodel: 4 vertici, 1 GT3, 1 GT4",
          len(m["verts"]) == 4 and len(m["tris"]) == 1 and len(m["quads"]) == 1)

    tmd_data = open(psxcd.extract_file(disc, dict(files)["MODEL.TMD"], out), "rb").read()
    objs = tmd2gltf.parse(tmd_data)
    check("tmd: 1 oggetto", len(objs) == 1)
    check("tmd: 3 vertici, 1 triangolo",
          len(objs[0]["verts"]) == 3 and len(objs[0]["tris"]) == 1)
    o = os.path.join(out, "MODEL.TMD")
    tmd2gltf.to_obj(objs, o + ".obj")
    tmd2gltf.to_gltf(objs, o + ".gltf")
    check("tmd: obj+gltf scritti", os.path.exists(o + ".obj") and os.path.exists(o + ".gltf"))

    # XA: fixture nota — shift=12 (stored 0), filtro 0, nibble 4 → campione 1 = 16384,
    # poi converge a 32767 per la retroazione f0=60.
    streams = {}
    for lba in range(disc.nsect):
        kind, data, sub = disc.sector(lba)
        if kind == "form2" and sub[2] & 0x04:
            key = (sub[0], sub[1])
            streams[key] = streams.get(key, b"") + data
    key = (1, 1)
    check("xa: 1 stream (file1,canale1)", list(streams.keys()) == [key])
    payload = streams[key]
    coding = 0x00
    samples, rate = xa_audio.decode_sector(payload[:2324], False, coding)
    check("xa: rate 37800", rate == 37800)
    exp = 16384
    exp_next = 16384 + ((16384 * 60 + 32) // 64)      # 31744, poi satura a 32767
    check("xa: primo campione 16384", samples[0] == exp)
    check("xa: retroazione filtro 1", samples[1] == exp_next)
    check("xa: saturazione a 32767", samples[2] == 32767)

    # directory ACE2 (unit): 2 entries costruite a mano
    e0 = (0x0000000A) | (0 << 28) | (5 << 32)          # size/4=10 → 40 byte, ch0, off 5 blocchi
    e1 = (0x00000002) | (3 << 28) | (9 << 32)          # size/2048=2 → 4096, ch3, off 9
    dir_ace = struct.pack("<II", 1, 2) + struct.pack("<QQ", e0, e1) + b"\x00" * 32
    unk, ents = ace2arc.parse_dir(dir_ace, "DAT")
    check("ace2: 2 entries", len(ents) == 2)
    check("ace2: size DAT ×4", ents[0]["size"] == 40 and ents[0]["off"] == 5 * 2048)
    _, ents2 = ace2arc.parse_dir(dir_ace, "STP")
    check("ace2: size STP ×2048", ents2[1]["size"] == 4096 and ents2[1]["chan"] == 3)

    n_pass = sum(1 for _, v in ok if v)
    print(f"\n{n_pass}/{len(ok)} test passati")
    return 0 if n_pass == len(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
