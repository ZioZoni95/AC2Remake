#!/usr/bin/env python3
"""mipsdis — mini disassemblatore MIPS R3000 (little endian), solo stdlib.

Copre le istruzioni comuni del codice di gioco PSX (non GTE/COP0 dettagliati: appaiono come .word).
Uso: mipsdis.py FILE BASE_ADDR [OFFSET [N_ISTR]]   (FILE = EXE/overlay grezzo, BASE_ADDR in hex)
"""
import struct, sys

REG = ["zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
       "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"]
RFUN = {0x00:"sll",0x02:"srl",0x03:"sra",0x04:"sllv",0x06:"srlv",0x07:"srav",0x08:"jr",0x09:"jalr",
        0x0C:"syscall",0x0D:"break",0x10:"mfhi",0x11:"mthi",0x12:"mflo",0x13:"mtlo",0x18:"mult",
        0x19:"multu",0x1A:"div",0x1B:"divu",0x20:"add",0x21:"addu",0x22:"sub",0x23:"subu",
        0x24:"and",0x25:"or",0x26:"xor",0x27:"nor",0x2A:"slt",0x2B:"sltu"}
IOP = {0x08:"addi",0x09:"addiu",0x0A:"slti",0x0B:"sltiu",0x0C:"andi",0x0D:"ori",0x0E:"xori"}
MEM = {0x20:"lb",0x21:"lh",0x22:"lwl",0x23:"lw",0x24:"lbu",0x25:"lhu",0x26:"lwr",
       0x28:"sb",0x29:"sh",0x2A:"swl",0x2B:"sw",0x2E:"swr"}
BR2 = {0x04:"beq",0x05:"bne"}
BR1 = {0x06:"blez",0x07:"bgtz"}


def dis(w, pc):
    op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31; rd = (w >> 11) & 31
    sh = (w >> 6) & 31; fn = w & 63; imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    r = lambda i: "$" + REG[i]
    if w == 0: return "nop"
    if op == 0:
        n = RFUN.get(fn)
        if n is None: return f".word 0x{w:08x}"
        if n in ("sll","srl","sra"): return f"{n} {r(rd)}, {r(rt)}, {sh}"
        if n in ("sllv","srlv","srav"): return f"{n} {r(rd)}, {r(rt)}, {r(rs)}"
        if n == "jr": return f"jr {r(rs)}"
        if n == "jalr": return f"jalr {r(rd)}, {r(rs)}"
        if n in ("mfhi","mflo"): return f"{n} {r(rd)}"
        if n in ("mthi","mtlo"): return f"{n} {r(rs)}"
        if n in ("mult","multu","div","divu"): return f"{n} {r(rs)}, {r(rt)}"
        if n in ("syscall","break"): return n
        return f"{n} {r(rd)}, {r(rs)}, {r(rt)}"
    if op == 1:
        n = {0:"bltz",1:"bgez",16:"bltzal",17:"bgezal"}.get(rt)
        return f"{n} {r(rs)}, 0x{pc + 4 + simm * 4:08x}" if n else f".word 0x{w:08x}"
    if op == 2: return f"j 0x{((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2):08x}"
    if op == 3: return f"jal 0x{((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2):08x}"
    if op in BR2: return f"{BR2[op]} {r(rs)}, {r(rt)}, 0x{pc + 4 + simm * 4:08x}"
    if op in BR1: return f"{BR1[op]} {r(rs)}, 0x{pc + 4 + simm * 4:08x}"
    if op in IOP: return f"{IOP[op]} {r(rt)}, {r(rs)}, {simm if op in (8,9,10,11) else hex(imm)}"
    if op == 0x0F: return f"lui {r(rt)}, 0x{imm:04x}"
    if op in MEM: return f"{MEM[op]} {r(rt)}, {simm}({r(rs)})"
    return f".word 0x{w:08x}"


def disasm_range(data, base, off=0, n=None):
    n = n if n is not None else (len(data) - off) // 4
    out = []
    for i in range(n):
        o = off + i * 4
        if o + 4 > len(data): break
        w = struct.unpack_from("<I", data, o)[0]
        out.append((base + o, w, dis(w, base + o)))
    return out


if __name__ == "__main__":
    f, base = sys.argv[1], int(sys.argv[2], 16)
    off = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
    n = int(sys.argv[4]) if len(sys.argv) > 4 else None
    data = open(f, "rb").read()
    for a, w, t in disasm_range(data, base, off, n):
        print(f"{a:08x}: {w:08x}  {t}")
