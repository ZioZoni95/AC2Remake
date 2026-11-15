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
/* hook ad alto livello (HLE): funzioni del loader che parlano col controller CD; sostituite da 'ritorna subito con v0=ret' */
static struct { uint32_t addr; uint32_t ret; uint32_t cnt; unsigned long n; } hooks[16]; static int nhooks;
static void add_hook(uint32_t a, uint32_t r) { hooks[nhooks].addr = a; hooks[nhooks].ret = r; hooks[nhooks].cnt = 0; nhooks++; }
static void add_counter_hook(uint32_t a, uint32_t cnt) { add_hook(a, 0); hooks[nhooks - 1].cnt = cnt; }

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
        if (p >= 0x1f801100 && p < 0x1f801130 && (p & 15) == 0) return (uint32_t)(icount >> 1) & 0xffff;   /* root counter: avanza col tempo */
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

static int run(uint32_t start, uint32_t stop, unsigned long maxi) {
    icount = 0;
    pc = start; npc = pc + 4; R[31] = stop; ld_reg = 0;
    int err = 0;
    while (pc != stop && icount < maxi) {
        uint32_t cur = pc;
        /* chiamate BIOS: vettori 0xA0/0xB0/0xC0 e ROM */
        uint32_t pp = pc & 0x1fffffff;
        if (pp == 0xa0 || pp == 0xb0 || pp == 0xc0 || pp >= 0x1fc00000) { bios_calls++; R[2] = 0; pc = R[31]; npc = pc + 4; continue; }
        { int hk = 0; for (int i = 0; i < nhooks; i++) if (hooks[i].addr == pc) { hooks[i].n++; R[2] = hooks[i].ret; if (hooks[i].cnt) { uint32_t *c = (uint32_t *)&ram[hooks[i].cnt & (RAM_SIZE - 1)]; (*c)++; R[2] = *c; } pc = R[31]; npc = pc + 4; hk = 1; break; } if (hk) continue; }
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
            case 0x0c: setr(2, 1); break;   /* syscall: Enter/ExitCriticalSection del BIOS = no-op */
            case 0x0d: err = 2; break;
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
    return err;
}

static void dump_state(const char *path) {
    FILE *o = fopen(path, "wb"); if (!o) return; uint32_t h2[35]; memcpy(h2, R, 128); h2[32] = pc; h2[33] = hi; h2[34] = lo;
    fwrite(h2, 4, 35, o); fwrite(ram, 1, RAM_SIZE, o); fwrite(sp, 1, 0x400, o);
    uint32_t g2[64]; for (int i = 0; i < 32; i++) { g2[i] = gte.data[i]; g2[32 + i] = gte.control[i]; } fwrite(g2, 4, 64, o);
    fclose(o);
}

/* --boot EXE MAX: carica un PS-X EXE come il BIOS (testo a load_addr, sp, pc = entry) ed esegue; stampa dove finisce e gli I/O toccati.
 * Serve a costruire lo stato iniziale SENZA snapshot (SCOPERTE #35): il loader del gioco legge poi il disco. */
static int do_boot(const char *exe, unsigned long maxi) {
    FILE *f = fopen(exe, "rb"); if (!f) { perror("exe"); return 1; }
    uint32_t h[0x800 / 4]; if (fread(h, 1, 0x800, f) != 0x800 || memcmp(h, "PS-X EXE", 8)) { fprintf(stderr, "non e' un PS-X EXE\n"); return 1; }
    uint32_t entry = h[4], gpv = h[5], addr = h[6], size = h[7], spv = h[12];
    if (fread(&ram[addr & (RAM_SIZE - 1)], 1, size, f) != size) { fprintf(stderr, "EXE troncato\n"); return 1; }
    fclose(f); gte_init(&gte);
    memset(R, 0, sizeof R); R[28] = gpv; R[29] = spv ? spv : 0x801fff00; R[30] = R[29];
    fprintf(stderr, "boot: entry %08x gp %08x load %08x size %x sp %08x\n", entry, gpv, addr, size, R[29]);
    add_hook(0x801d9068, 2); add_hook(0x801d91f4, 1); add_hook(0x801d9458, 1); add_hook(0x801dbe40, 0); add_counter_hook(0x801dc3b4, 0x801df8f8);
    int err = run(entry, 0xdeadbeef, maxi);
    for (int i = 0; i < nhooks; i++) fprintf(stderr, "hook %08x chiamato %lu volte\n", hooks[i].addr, hooks[i].n);
    fprintf(stderr, "boot finito: err=%d pc=%08x istruzioni=%lu io_letture=%lu io_scritture=%lu bios=%lu ultimo_io=%08x ra=%08x\n", err, pc, icount, io_reads, io_writes, bios_calls, last_io, R[31]);
    return err;
}

int main(int argc, char **argv) {
    int boot = argc >= 4 && !strcmp(argv[1], "--boot");
    if (boot) return do_boot(argv[2], strtoul(argv[3], 0, 0));
    int serve = argc >= 3 && !strcmp(argv[1], "--serve"); if (serve) { argv++; argc--; }
    if (!serve && argc != 6) { fprintf(stderr, "uso: mipsvm STATO START STOP MAX OUT | mipsvm --serve STATO [EXPORT]\n"); return 2; }
    FILE *f = fopen(argv[1], "rb"); if (!f) { perror("stato"); return 1; }
    uint32_t hdr[35];
    if (fread(hdr, 4, 35, f) != 35) return 1;
    memcpy(R, hdr, 128); hi = hdr[33]; lo = hdr[34];
    if (fread(ram, 1, RAM_SIZE, f) != RAM_SIZE || fread(sp, 1, 0x400, f) != 0x400) return 1;
    gte_init(&gte);
    uint32_t g[64];
    if (fread(g, 4, 64, f) == 64) { for (int i = 0; i < 32; i++) { gte.data[i] = g[i]; gte.control[i] = g[32 + i]; } }
    fclose(f);
    if (serve) {
        /* servizio: da stdin righe "F TASTI" (un fotogramma originale con i tasti PS1 dati), "Q" per uscire.
         * Dopo ogni fotogramma scrive EXPORT (default /tmp/ac2_state.bin, scrittura atomica) = formato di ac2_remote.lua:
         * [u32 frame][giocatore 0x3f8][63 slot x 0x174][camera 0x60]. Il contatore parte da 0 e cresce di 1 a fotogramma. */
        const char *ex = argc > 2 ? argv[2] : "/tmp/ac2_state.bin"; char tmp[512]; snprintf(tmp, sizeof tmp, "%s.tmp", ex);
        char line[128]; uint32_t frame = 0;
        while (fgets(line, sizeof line, stdin)) {
            if (line[0] == 'Q') break;
            if (line[0] == 'S') { char *e = line + 1; while (*e == ' ') e++; e[strcspn(e, "\r\n")] = 0; dump_state(e); printf("salvato\n"); fflush(stdout); continue; }
            if (line[0] != 'F') continue;
            uint32_t btn = (uint32_t)strtoul(line + 1, 0, 0), inv = ~btn;
            ram[0xb9040] = 0; ram[0xb9041] = 0x41; ram[0xb9042] = inv & 0xff; ram[0xb9043] = (inv >> 8) & 0xff;
            if (run(0x8005f6a4, 0x80010000, 1000000) || run(0x8002a1f4, 0x8002a16c, 5000000)) return 1;
            uint32_t pl; memcpy(&pl, &ram[0xb84ac], 4); uint32_t pool; memcpy(&pool, &ram[0xb8748], 4);
            FILE *o = fopen(tmp, "wb"); if (!o) return 1;
            fwrite(&frame, 4, 1, o); fwrite(&ram[pl & (RAM_SIZE - 1)], 1, 0x3f8, o);
            fwrite(&ram[pool & (RAM_SIZE - 1)], 1, 63 * 0x174, o); fwrite(&ram[0xbc5a0], 1, 0x60, o); fclose(o);
            rename(tmp, ex); frame++;
            printf("ok %u\n", frame); fflush(stdout);
        }
        return 0;
    }
    uint32_t start = strtoul(argv[2], 0, 16), stop = strtoul(argv[3], 0, 16); unsigned long maxi = strtoul(argv[4], 0, 0);
    int err = run(start, stop, maxi);
    fprintf(stderr, "fine: pc=%08x istruzioni=%lu io_letture=%lu io_scritture=%lu bios=%lu ultimo_io=%08x\n", pc, icount, io_reads, io_writes, bios_calls, last_io);
    FILE *o = fopen(argv[5], "wb"); uint32_t h2[35]; memcpy(h2, R, 128); h2[32] = pc; h2[33] = hi; h2[34] = lo;
    fwrite(h2, 4, 35, o); fwrite(ram, 1, RAM_SIZE, o); fwrite(sp, 1, 0x400, o);
    uint32_t g2[64]; for (int i = 0; i < 32; i++) { g2[i] = gte.data[i]; g2[32 + i] = gte.control[i]; } fwrite(g2, 4, 64, o);
    fclose(o); return err ? 1 : 0;
}
