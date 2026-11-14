#!/usr/bin/env python3
"""tim2png — decodifica immagini TIM (PSX) in PNG.

Formato TIM (Sony Filefrmt): header u32 0x10, flag u32 (bit0-2 pixel mode,
bit3 CLUT presente), poi blocco CLUT e blocco immagine:
  blocco: u32 len (include i 12 byte di header), s16 x, s16 y, u16 w, u16 h
  w e' in unita' da 16 bit: 4bpp=4px/unita', 8bpp=2, 16bpp=1, 24bpp=w*2 byte/riga
CLUT: entry u16 BGR555 (bit15 STP ignorato).
"""
import struct
import sys

from pngout import write_png


def _rgb555(c):
    r = (c & 31) * 255 // 31
    g = ((c >> 5) & 31) * 255 // 31
    b = ((c >> 10) & 31) * 255 // 31
    return r, g, b


def decode(data):
    if len(data) < 8 or struct.unpack_from("<I", data, 0)[0] != 0x10:
        raise ValueError("non e' un TIM (magic 0x10 mancante)")
    flag = struct.unpack_from("<I", data, 4)[0]
    pmode = flag & 0x7
    has_clut = bool(flag & 0x8)
    pos = 8
    clut = None
    if has_clut:
        blen, _x, _y, _w, _h = struct.unpack_from("<IhhHH", data, pos)
        n = (blen - 12) // 2
        clut = [_rgb555(struct.unpack_from("<H", data, pos + 12 + 2 * i)[0]) for i in range(n)]
        pos += blen
    blen, _x, _y, w, h = struct.unpack_from("<IhhHH", data, pos)
    body = data[pos + 12:pos + blen]
    rows = []
    if pmode == 2:  # 16bpp dirette
        for r in range(h):
            row = bytearray()
            for c in range(w):
                row.extend(_rgb555(struct.unpack_from("<H", body, (r * w + c) * 2)[0]))
            rows.append(bytes(row))
        width = w
    elif pmode in (0, 1):  # 4bpp / 8bpp con CLUT
        ppu = 4 if pmode == 0 else 2
        width = w * ppu
        for r in range(h):
            row = bytearray()
            base = r * w * 2
            for c in range(width):
                if pmode == 0:
                    byte = body[base + c // 2]
                    idx = byte >> ((c % 2) * 4) & 0xF
                else:
                    idx = body[base + c]
                row.extend(clut[idx] if clut and idx < len(clut) else (255, 0, 255))
            rows.append(bytes(row))
    elif pmode == 3:  # 24bpp: w in unita' 16-bit, 3 byte per pixel
        width = w * 2 // 3
        for r in range(h):
            row = bytearray()
            base = r * w * 2
            for c in range(width):
                row.extend(body[base + c * 3: base + c * 3 + 3])
            rows.append(bytes(row))
    else:
        raise ValueError(f"pixel mode {pmode} (mixed) non supportato")
    return width, h, rows


def to_png(data, out):
    w, h, rows = decode(data)
    write_png(out, w, h, rows)
    return w, h


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    w, h = to_png(open(src, "rb").read(), dst)
    print(f"{dst}: {w}x{h}")
