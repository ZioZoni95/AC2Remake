/* mipsvm — interprete MIPS R3000 minimo per eseguire il codice originale di Ace Combat 2 su uno snapshot di memoria.
 * Uso: mipsvm STATO.bin START_PC STOP_PC MAX_ISTR OUT.bin   (indirizzi in hex)
 * STATO.bin = [regs u32 x32][pc][hi][lo][RAM 2 MiB][scratchpad 1 KiB][gte data u32 x32][gte control u32 x32]
 * Esegue da START_PC con ra = STOP_PC finche' pc == STOP_PC; scrive lo stato finale (stesso formato) in OUT.bin.
 * Hardware: I/O ignorato (letture = 0); chiamate BIOS (0xA0/0xB0/0xC0, ROM) = ritorno con v0 = 0. GTE: da gte.c dell'emulatore. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "gte.h"

#define RAM_SIZE 0x200000
static uint8_t ram[RAM_SIZE], sp[0x400];
static uint32_t R[32], pc, npc, hi, lo, ld_reg, ld_val;
static Gte gte;
static unsigned long icount, io_reads, io_writes, bios_calls, unk;
static uint32_t last_io;

static uint8_t *ptr(uint32_t a, int *io) {
    uint32_t p = a & 0x1fffffff; *io = 0;
    if (p < 0x800000) return &ram[p & (RAM_SIZE - 1)];
    if (p >= 0x1f800000 && p < 0x1f800400) return &sp[p - 0x1f800000];
    *io = 1; return NULL;
}
static uint32_t rd(uint32_t a, int sz) {
    int io; uint8_t *p = ptr(a, &io);
    if (io) {
        io_reads++; last_io = a;
        uint32_t p = a & 0x1fffffff;
        if (p == 0x1f801814) return 0x1c000000;      /* GPUSTAT: pronta a comandi, a DMA e a dati */
        return 0;
    }
    uint32_t v = 0; memcpy(&v, p, sz); return v;
}
static void wr(uint32_t a, uint32_t v, int sz) {
    int io; uint8_t *p = ptr(a, &io);
    if (io) { io_writes++; return; }
    memcpy(p, &v, sz);
}
#define SX16(x) ((int32_t)(int16_t)(x))
#define SX8(x) ((int32_t)(int8_t)(x))

static void setr(int r, uint32_t v) { if (r) R[r] = v; }

int main(int argc, char **argv) {
    if (argc != 6) { fprintf(stderr, "uso: mipsvm STATO START STOP MAX OUT\n"); return 2; }
    FILE *f = fopen(argv[1], "rb"); if (!f) { perror("stato"); return 1; }
    uint32_t hdr[35];
    if (fread(hdr, 4, 35, f) != 35) return 1;
    memcpy(R, hdr, 128); hi = hdr[33]; lo = hdr[34];
    if (fread(ram, 1, RAM_SIZE, f) != RAM_SIZE || fread(sp, 1, 0x400, f) != 0x400) return 1;
    gte_init(&gte);
    uint32_t g[64];
    if (fread(g, 4, 64, f) == 64) { for (int i = 0; i < 32; i++) { gte.data[i] = g[i]; gte.control[i] = g[32 + i]; } }
    fclose(f);
    uint32_t start = strtoul(argv[2], 0, 16), stop = strtoul(argv[3], 0, 16); unsigned long maxi = strtoul(argv[4], 0, 0);
    pc = start; npc = pc + 4; R[31] = stop; ld_reg = 0;
    int err = 0;
    while (pc != stop && icount < maxi) {
        uint32_t cur = pc;
        /* chiamate BIOS: vettori 0xA0/0xB0/0xC0 e ROM */
        uint32_t pp = pc & 0x1fffffff;
        if (pp == 0xa0 || pp == 0xb0 || pp == 0xc0 || pp >= 0x1fc00000) { bios_calls++; R[2] = 0; pc = R[31]; npc = pc + 4; continue; }
        uint32_t ins = rd(pc, 4);
        uint32_t next = npc; npc = npc + 4;
        /* gestione ritardo di caricamento: il valore caricato diventa visibile dopo l'istruzione successiva */
        int pend_reg = ld_reg; uint32_t pend_val = ld_val; ld_reg = 0;
        uint32_t op = ins >> 26, rs = (ins >> 21) & 31, rt = (ins >> 16) & 31, rdn = (ins >> 11) & 31, sh = (ins >> 6) & 31, fn = ins & 63;
        int32_t imm = SX16(ins & 0xffff); uint32_t uimm = ins & 0xffff;
        uint32_t a = R[rs], b = R[rt];
        pc = next;
        int taken = 0; uint32_t target = 0;
        switch (op) {
        case 0:
            switch (fn) {
            case 0x00: setr(rdn, b << sh); break; case 0x02: setr(rdn, b >> sh); break; case 0x03: setr(rdn, (int32_t)b >> sh); break;
            case 0x04: setr(rdn, b << (a & 31)); break; case 0x06: setr(rdn, b >> (a & 31)); break; case 0x07: setr(rdn, (int32_t)b >> (a & 31)); break;
            case 0x08: taken = 1; target = a; break;
            case 0x09: setr(rdn, cur + 8); taken = 1; target = a; break;
            case 0x0c: case 0x0d: err = 2; break;
            case 0x10: setr(rdn, hi); break; case 0x11: hi = a; break; case 0x12: setr(rdn, lo); break; case 0x13: lo = a; break;
            case 0x18: { int64_t p = (int64_t)(int32_t)a * (int32_t)b; lo = (uint32_t)p; hi = (uint32_t)(p >> 32); } break;
            case 0x19: { uint64_t p = (uint64_t)a * b; lo = (uint32_t)p; hi = (uint32_t)(p >> 32); } break;
            case 0x1a: if (b) { lo = (uint32_t)((int32_t)a / (int32_t)b); hi = (uint32_t)((int32_t)a % (int32_t)b); } else { lo = ((int32_t)a < 0) ? 1 : 0xffffffff; hi = a; } break;
            case 0x1b: if (b) { lo = a / b; hi = a % b; } else { lo = 0xffffffff; hi = a; } break;
            case 0x20: case 0x21: setr(rdn, a + b); break; case 0x22: case 0x23: setr(rdn, a - b); break;
            case 0x24: setr(rdn, a & b); break; case 0x25: setr(rdn, a | b); break; case 0x26: setr(rdn, a ^ b); break; case 0x27: setr(rdn, ~(a | b)); break;
            case 0x2a: setr(rdn, (int32_t)a < (int32_t)b); break; case 0x2b: setr(rdn, a < b); break;
            default: err = 1; }
            break;
        case 1: { int cond = (rt & 1) ? ((int32_t)a >= 0) : ((int32_t)a < 0); if ((rt & 0x1e) == 0x10) setr(31, cur + 8);
                  if (cond) { taken = 1; target = cur + 4 + (imm << 2); } } break;
        case 2: taken = 1; target = ((cur + 4) & 0xf0000000) | ((ins & 0x3ffffff) << 2); break;
        case 3: setr(31, cur + 8); taken = 1; target = ((cur + 4) & 0xf0000000) | ((ins & 0x3ffffff) << 2); break;
        case 4: if (a == b) { taken = 1; target = cur + 4 + (imm << 2); } break;
        case 5: if (a != b) { taken = 1; target = cur + 4 + (imm << 2); } break;
        case 6: if ((int32_t)a <= 0) { taken = 1; target = cur + 4 + (imm << 2); } break;
        case 7: if ((int32_t)a > 0) { taken = 1; target = cur + 4 + (imm << 2); } break;
        case 8: case 9: setr(rt, a + imm); break; case 10: setr(rt, (int32_t)a < imm); break; case 11: setr(rt, a < (uint32_t)imm); break;
        case 12: setr(rt, a & uimm); break; case 13: setr(rt, a | uimm); break; case 14: setr(rt, a ^ uimm); break; case 15: setr(rt, uimm << 16); break;
        case 16: if (rs == 0) setr(rt, 0); break;                       /* COP0: mfc0 -> 0, mtc0/rfe ignorati */
        case 18:                                                        /* COP2 = GTE */
            if (ins & 0x2000000) gte_execute_instruction(&gte, ins);
            else if (rs == 0) { ld_reg = rt; ld_val = (uint32_t)gte_read_data_register(&gte, rdn); }
            else if (rs == 2) { ld_reg = rt; ld_val = (uint32_t)gte_read_control_register(&gte, rdn); }
            else if (rs == 4) gte_write_data_register(&gte, rdn, (int32_t)b);
            else if (rs == 6) gte_write_control_register(&gte, rdn, (int32_t)b);
            else err = 1;
            break;
        case 0x20: ld_reg = rt; ld_val = SX8(rd(a + imm, 1)); break;
        case 0x21: ld_reg = rt; ld_val = SX16(rd(a + imm, 2)); break;
        case 0x22: { uint32_t ad = a + imm, w = rd(ad & ~3, 4), cv = (pend_reg == (int)rt && rt) ? pend_val : R[rt]; int k = ad & 3;
                     ld_reg = rt; ld_val = (cv & (0x00ffffff >> (8 * (3 - k)))) | (w << (8 * (3 - k))); } break;
        case 0x23: ld_reg = rt; ld_val = rd(a + imm, 4); break;
        case 0x24: ld_reg = rt; ld_val = rd(a + imm, 1); break;
        case 0x25: ld_reg = rt; ld_val = rd(a + imm, 2); break;
        case 0x26: { uint32_t ad = a + imm, w = rd(ad & ~3, 4), cv = (pend_reg == (int)rt && rt) ? pend_val : R[rt]; int k = ad & 3;
                     ld_reg = rt; ld_val = (cv & (0xffffff00u << (8 * k))) | (w >> (8 * k)); } break;
        case 0x28: wr(a + imm, b, 1); break; case 0x29: wr(a + imm, b, 2); break;
        case 0x2a: { uint32_t ad = a + imm, w = rd(ad & ~3, 4); int k = ad & 3; w = (w & (0xffffff00u << (8 * (k + 1)))) | (b >> (8 * (3 - k))); if (k == 3) w = b; wr(ad & ~3, w, 4); } break;
        case 0x2b: wr(a + imm, b, 4); break;
        case 0x2e: { uint32_t ad = a + imm, w = rd(ad & ~3, 4); int k = ad & 3; w = (w & (0x00ffffffu >> (8 * (3 - k)))) | (b << (8 * k)); wr(ad & ~3, w, 4); } break;
        case 0x32: gte_write_data_register(&gte, rt, (int32_t)rd(a + imm, 4)); break;      /* LWC2 */
        case 0x3a: wr(a + imm, (uint32_t)gte_read_data_register(&gte, rt), 4); break;      /* SWC2 */
        default: err = 1;
        }
        if (pend_reg) R[pend_reg] = pend_val;
        R[0] = 0;
        if (taken) { npc = target; }
        icount++;
        if (err) { fprintf(stderr, "ERRORE codice %d: istruzione %08x a pc=%08x dopo %lu istruzioni\n", err, ins, cur, icount); break; }
    }
    fprintf(stderr, "fine: pc=%08x istruzioni=%lu io_letture=%lu io_scritture=%lu bios=%lu ultimo_io=%08x\n", pc, icount, io_reads, io_writes, bios_calls, last_io);
    FILE *o = fopen(argv[5], "wb"); uint32_t h2[35]; memcpy(h2, R, 128); h2[32] = pc; h2[33] = hi; h2[34] = lo;
    fwrite(h2, 4, 35, o); fwrite(ram, 1, RAM_SIZE, o); fwrite(sp, 1, 0x400, o);
    uint32_t g2[64]; for (int i = 0; i < 32; i++) { g2[i] = gte.data[i]; g2[32 + i] = gte.control[i]; } fwrite(g2, 4, 64, o);
    fclose(o); return err ? 1 : 0;
}
