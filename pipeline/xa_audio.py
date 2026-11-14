#!/usr/bin/env python3
"""xa_audio — carving + decodifica CD-XA ADPCM da immagine CD raw.

Specifica ADPCM: psx-spx cdromformat.md "CDROM XA Audio ADPCM Compression":
  - settore form2 audio: payload 2324 byte = 18 porzioni da 128 byte + 20 pad
  - porzione: 16 byte header (byte 4..7 = shift/filtro per 4 blocchi, copie a 0..3 e 8..11)
              + 28 word da 32 bit: per word j, il nibble del blocco b sta nel byte 16+b+j*4
  - 4bit: shift = 12 - (hdr & 0x0F), filtro = (hdr >> 4) & 3
  - stereo: nibble basso = Left, nibble alto = Right; mono: due meta' in sequenza
  - filtri: pos (0,60,115,98,122), neg (0,0,-52,-55,-60)
"""
import os
import struct
import wave

POS = (0, 60, 115, 98, 122)
NEG = (0, 0, -52, -55, -60)
PORTIONS = 18
SAMPLES_PER_SECTOR = PORTIONS * 4 * 28  # 2016 halfword


def _sgn4(v):
    return v - 16 if v & 0x8 else v


def decode_sector(payload, stereo, coding):
    """payload: 2324 byte. Ritorna campioni intercalati L,R (o mono duplicati)."""
    rate_hz = 18900 if (coding >> 2) & 1 else 37800
    bits8 = (coding >> 4) & 1
    if bits8:
        raise NotImplementedError("XA-ADPCM 8bit non ancora supportato")

    def stream(nib, blk_headers, data, old, older):
        samples = []
        for blk in range(4):
            hdr = blk_headers[blk * 2 + nib]
            shift = 12 - (hdr & 0x0F)
            filt = (hdr >> 4) & 0x3
            f0, f1 = POS[filt], NEG[filt]
            for j in range(28):
                b = data[16 + blk + j * 4]
                t = _sgn4((b >> (nib * 4)) & 0x0F)
                s = (t << shift) + ((old * f0 + older * f1 + 32) // 64)
                s = max(-32768, min(32767, s))
                samples.append(s)
                older, old = old, s
        return samples, old, older

    out = []
    oL = oLd = oR = oRd = 0
    for i in range(PORTIONS):
        base = i * 128
        hdrs = payload[base + 4:base + 12]
        data = payload[base:base + 128]
        if stereo:
            sl, oL, oLd = stream(0, hdrs, data, oL, oLd)
            sr, oR, oRd = stream(1, hdrs, data, oR, oRd)
            for a, b in zip(sl, sr):
                out.extend((a, b))
        else:
            sm, oL, oLd = stream(0, hdrs, data, oL, oLd)
            sm2, oR, oRd = stream(1, hdrs, data, oR, oRd)
            out.extend(sm)
            out.extend(sm2)
    return out, rate_hz


def write_wav(path, samples, rate, stereo):
    with wave.open(path, "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def carve(disc, keep_raw=False, outdir="assets/audio"):
    """Scansiona l'immagine, raggruppa i settori XA-audio per (file,canale) e decodifica."""
    streams = {}
    for lba in range(disc.nsect):
        kind, data, sub = disc.sector(lba)
        if kind != "form2" or not (sub[2] & 0x04):  # submode bit Audio
            continue
        key = (sub[0], sub[1])
        if key not in streams:
            streams[key] = dict(payload=b"", coding=sub[3], lba0=lba, count=0)
        streams[key]["payload"] += data
        streams[key]["count"] += 1
    os.makedirs(outdir, exist_ok=True)
    results = []
    for (fnum, chan), s in sorted(streams.items()):
        try:
            samples, rate = decode_sector_payload(s)
            stereo = (s["coding"] & 1) == 1
            name = f"xa_f{fnum:02d}_c{chan:02d}.wav"
            write_wav(os.path.join(outdir, name), samples, rate, stereo)
            results.append((fnum, chan, s["count"], rate, stereo, name))
        except NotImplementedError:
            name = f"xa_f{fnum:02d}_c{chan:02d}.raw"
            if keep_raw or True:
                with open(os.path.join(outdir, name), "wb") as fh:
                    fh.write(s["payload"])
            results.append((fnum, chan, s["count"], None, None, name))
    return results


def decode_sector_payload(s):
    stereo = (s["coding"] & 1) == 1
    out = []
    rate = None
    n = 2324
    p = s["payload"]
    # decodifica a blocchi di settore
    decoded = []
    for i in range(s["count"]):
        chunk = p[i * n:(i + 1) * n]
        samples, rate = decode_sector(chunk, stereo, s["coding"])
        decoded.extend(samples)
    return decoded, rate
