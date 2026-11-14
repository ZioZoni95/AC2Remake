#!/usr/bin/env python3
"""psxcd — lettore di immagini CD raw (.bin 2352) + filesystem ISO9660 + carving XA.

Specifica: psx-spx (cdromformat.md, cdromfileformats.md) — clone locale in
~/GitHub/ZonistationOne/psx-spx.github.io.

Settore raw 2352 byte:
  0..11  sync (00 FF*10 00)
  12..15 header: min, sec, frame (BCD), mode (1 o 2)
  mode1:  dati utente 2048 byte a +16 (ISO9660)
  mode2:  subheader 8 byte a +16 (file, channel, submode, codinginfo), poi
          form1 (submode bit5=0): 2048 byte dati a +24
          form2 (submode bit5=1): 2324 byte (0x914) a +24 (XA audio/video)

Submode (psx-spx): bit0 EOR, bit1 Video, bit2 Audio, bit3 Data, bit4 Trigger,
bit5 Form2, bit6 RealTime, bit7 EOF.
"""
import os
import struct

SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
RAW = 2352

SUBMODE_AUDIO = 0x04
SUBMODE_VIDEO = 0x02
SUBMODE_DATA = 0x10
SUBMODE_FORM2 = 0x20


class Disc:
    def __init__(self, path):
        self.f = open(path, "rb")
        self.f.seek(0, 2)
        size = self.f.tell()
        self.path = path
        self.nsect = size // RAW
        self.extra = size % RAW

    def raw(self, lba):
        self.f.seek(lba * RAW)
        data = self.f.read(RAW)
        if len(data) < RAW:
            raise IOError(f"settore {lba} fuori immagine")
        if data[:12] != SYNC:
            raise IOError(f"settore {lba}: sync mancante (immagine corrotta?)")
        return data

    def sector(self, lba):
        """Ritorna (kind, payload, subheader) con kind in data/form1/form2."""
        raw = self.raw(lba)
        mode = raw[15]
        if mode == 1:
            return "data", raw[16:16 + 2048], None
        if mode == 2:
            sub = raw[16:24]
            if sub[2] & SUBMODE_FORM2:
                return "form2", raw[24:24 + 2324], sub
            return "form1", raw[24:24 + 2048], sub
        raise ValueError(f"settore {lba}: mode={mode}")

    def block(self, lba):
        """I 2048 byte logici ISO9660 di un settore."""
        kind, data, _ = self.sector(lba)
        if kind == "form2":
            raise ValueError(f"settore {lba}: form2 nel flusso ISO")
        return data

    def close(self):
        self.f.close()


def _to_lba_msf(raw, lba):
    """Verifica allineamento MSF del settore (diagnostica)."""
    m, s, fr = raw[12], raw[13], raw[14]
    want = lba + 150
    got = (m * 60 + s) * 75 + fr
    return got == want, f"{m:02x}:{s:02x}:{fr:02x}"


class Entry:
    __slots__ = ("name", "lba", "size", "is_dir", "hidden")

    def __init__(self, name, lba, size, is_dir, hidden=False):
        self.name, self.lba, self.size, self.is_dir, self.hidden = name, lba, size, is_dir, hidden

    def __repr__(self):
        kind = "DIR " if self.is_dir else "FILE"
        return f"{kind} {self.name:<16} lba={self.lba:<8} size={self.size}"


def parse_dir_records(data, base_lba):
    """Record directory ISO9660: attenzione, i record non attraversano i blocchi."""
    out = []
    pos = 0
    while pos < len(data):
        ln = data[pos]
        if ln == 0:  # riempimento a fine blocco: salta al blocco successivo
            pos = (pos // 2048 + 1) * 2048
            if pos >= len(data):
                break
            continue
        rec = data[pos:pos + ln]
        lba = struct.unpack_from("<I", rec, 2)[0]
        size = struct.unpack_from("<I", rec, 10)[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33 + nlen].decode("latin-1")
        if name in ("", "\x00", "\x01"):  # root e parent
            pos += ln
            continue
        name = name.split(";")[0]
        out.append(Entry(name, lba, size, bool(flags & 2), bool(flags & 1)))
        pos += ln
    return out


def list_all(disc, path="/"):
    """Ritorna [{path, entry}] per tutto l'albero."""
    files = []
    def walk(lba, size, prefix):
        data = b""
        for i in range((size + 2047) // 2048):
            data += disc.block(lba + i)
        for e in parse_dir_records(data, lba):
            p = prefix + e.name
            if e.is_dir:
                walk(e.lba, e.size, p + "/")
            else:
                files.append((p, e))
    root = _root_dir(disc)
    walk(root.lba, root.size, path)
    return files


def _root_dir(disc):
    pvd = disc.block(16)
    if pvd[0] != 1 or pvd[1:6] != b"CD001":
        raise ValueError("PVD ISO9660 non trovato a LBA 16 (non e' un disco PSX?)")
    rec = pvd[156:156 + 34]
    lba = struct.unpack_from("<I", rec, 2)[0]
    size = struct.unpack_from("<I", rec, 10)[0]
    return Entry("/", lba, size, True)


def extract_file(disc, e, outdir, dest=None):
    """Estrae un file gestendo settori mode1 e mode2/form1 (e form2 grezzi)."""
    dest = dest or os.path.join(outdir, e.name.replace("/", "_"))
    os.makedirs(outdir, exist_ok=True)
    with open(dest, "wb") as out:
        left = e.size
        lba = e.lba
        while left > 0:
            kind, data, _ = disc.sector(lba)
            n = min(len(data), left)
            out.write(data[:n])          # l'ultima parte può non riempire il settore
            left -= n
            lba += 1
    return dest


def iter_sectors(disc):
    for lba in range(disc.nsect):
        yield lba, disc.sector(lba)
