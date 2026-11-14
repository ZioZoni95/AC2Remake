#!/usr/bin/env python3
"""pngout — PNG writer zero-dipendenze (stdlib zlib).

Scrive PNG RGB 8-bit con filtro 0. Usato da tim2png.py.
"""
import struct, zlib


def write_png(path, width, height, rows_rgb):
    """rows_rgb: lista di bytes RGBA inutilizzati... no: bytes RGB per riga."""
    raw = bytearray()
    for row in rows_rgb:
        raw.append(0)  # filtro 0 (None)
        raw.extend(row)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # bitdepth 8, RGB
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
           chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
