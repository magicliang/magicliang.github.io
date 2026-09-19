#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MEM_SIZE 4096u
#define MAX_TEXT_WORDS 256u
#define MAX_STEPS 1000u

typedef struct {
    uint32_t pc;
    uint32_t x[32];
    uint8_t mem[MEM_SIZE];
    uint32_t text[MAX_TEXT_WORDS];
    uint32_t text_words;
} Machine;

static uint32_t load32le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static void store32le(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static int64_t sext(uint32_t v, unsigned bits) {
    uint32_t mask = 1u << (bits - 1u);
    return (int64_t)(v ^ mask) - (int64_t)mask;
}

static uint32_t get_rd(uint32_t insn) { return (insn >> 7) & 31u; }
static uint32_t get_rs1(uint32_t insn) { return (insn >> 15) & 31u; }
static uint32_t get_rs2(uint32_t insn) { return (insn >> 20) & 31u; }
static uint32_t get_funct3(uint32_t insn) { return (insn >> 12) & 7u; }
static uint32_t get_funct7(uint32_t insn) { return (insn >> 25) & 127u; }

static int64_t imm_i(uint32_t insn) { return sext(insn >> 20, 12); }

static int64_t imm_s(uint32_t insn) {
    uint32_t raw = ((insn >> 7) & 31u) | (((insn >> 25) & 127u) << 5);
    return sext(raw, 12);
}

static int64_t imm_b(uint32_t insn) {
    uint32_t raw = (((insn >> 31) & 1u) << 12) |
                   (((insn >> 7) & 1u) << 11) |
                   (((insn >> 25) & 63u) << 5) |
                   (((insn >> 8) & 15u) << 1);
    return sext(raw, 13);
}

static bool slt32(uint32_t a, uint32_t b) {
    uint32_t sign_a = a >> 31;
    uint32_t sign_b = b >> 31;
    if (sign_a != sign_b) return sign_a > sign_b;
    return a < b;
}

static bool parse_u32(const char *s, uint32_t *out) {
    errno = 0;
    char *end = NULL;
    unsigned long v = strtoul(s, &end, 0);
    if (errno || end == s || v > UINT32_MAX) return false;
    while (*end == ' ' || *end == '\t') end++;
    if (*end != '\0') return false;
    *out = (uint32_t)v;
    return true;
}

static void strip_comment(char *line) {
    char *p = strchr(line, '#');
    if (p) *p = '\0';
    p = strchr(line, ';');
    if (p) *p = '\0';
}

static char *trim(char *s) {
    while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r') s++;
    char *end = s + strlen(s);
    while (end > s && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\n' || end[-1] == '\r')) {
        *--end = '\0';
    }
    return s;
}

static void load_program(const char *path, Machine *m) {
    FILE *f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "open %s: %s\n", path, strerror(errno));
        exit(2);
    }

    enum { MODE_TEXT, MODE_DATA } mode = MODE_TEXT;
    char line[256];
    unsigned lineno = 0;
    bool seen_data = false;
    while (fgets(line, sizeof line, f)) {
        lineno++;
        strip_comment(line);
        char *s = trim(line);
        if (!*s) continue;
        if (strcmp(s, ".text") == 0) {
            if (seen_data) {
                fprintf(stderr, "%s:%u: .text after .data is not supported\n", path, lineno);
                exit(2);
            }
            mode = MODE_TEXT;
            continue;
        }
        if (strcmp(s, ".data") == 0) {
            seen_data = true;
            mode = MODE_DATA;
            continue;
        }

        if (mode == MODE_TEXT) {
            if (m->text_words >= MAX_TEXT_WORDS) {
                fprintf(stderr, "%s:%u: too many text words\n", path, lineno);
                exit(2);
            }
            uint32_t word = 0;
            if (!parse_u32(s, &word)) {
                fprintf(stderr, "%s:%u: bad instruction word '%s'\n", path, lineno, s);
                exit(2);
            }
            m->text[m->text_words++] = word;
            store32le(&m->mem[(m->text_words - 1u) * 4u], word);
        } else {
            char *addr_s = strtok(s, " \t");
            char *word_s = strtok(NULL, " \t");
            char *extra_s = strtok(NULL, " \t");
            if (!addr_s || !word_s || extra_s) {
                fprintf(stderr, "%s:%u: data line must be '<addr> <word>'\n", path, lineno);
                exit(2);
            }
            uint32_t addr = 0, word = 0;
            if (!parse_u32(addr_s, &addr) || !parse_u32(word_s, &word) || addr > MEM_SIZE - 4u ||
                addr % 4u || addr < m->text_words * 4u) {
                fprintf(stderr, "%s:%u: bad data word at '%s %s'\n", path, lineno, addr_s, word_s);
                exit(2);
            }
            store32le(&m->mem[addr], word);
        }
    }
    fclose(f);
}

static void fail_json(uint32_t step, uint32_t pc, uint32_t insn, const char *reason) {
    printf("{\"step\":%" PRIu32 ",\"pc\":%" PRIu32 ",\"inst\":\"0x%08" PRIx32 "\",\"error\":\"%s\"}\n",
           step, pc, insn, reason);
}

static void write_reg(Machine *m, uint32_t rd, uint32_t value) {
    if (rd != 0) m->x[rd] = value;
    m->x[0] = 0;
}

static int run(Machine *m) {
    for (uint32_t step = 0; step < MAX_STEPS; step++) {
        if (m->pc == m->text_words * 4u) {
            printf("{\"halt\":\"pc_at_end\",\"steps\":%" PRIu32 ",\"x0\":%" PRIu32 ",\"x1\":%" PRIu32 ",\"x3\":%" PRIu32 ",\"mem148\":%" PRIu32 ",\"mem160\":%" PRIu32 "}\n",
                   step, m->x[0], m->x[1], m->x[3], load32le(&m->mem[148]), load32le(&m->mem[160]));
            return 0;
        }
        if (m->pc % 4u || m->pc + 4u > MEM_SIZE || m->pc / 4u >= m->text_words) {
            fail_json(step, m->pc, 0, "pc_out_of_text");
            return 1;
        }

        uint32_t pc0 = m->pc;
        uint32_t insn = m->text[m->pc / 4u];
        uint32_t opcode = insn & 127u;
        uint32_t rd = get_rd(insn), rs1 = get_rs1(insn), rs2 = get_rs2(insn);
        uint32_t f3 = get_funct3(insn), f7 = get_funct7(insn);
        uint32_t next_pc = m->pc + 4u;
        const char *mn = NULL;
        char event[96] = "";

        switch (opcode) {
        case 0x33: {
            uint32_t value = 0;
            if (f3 == 0 && f7 == 0x00) {
                mn = "add";
                value = m->x[rs1] + m->x[rs2];
            } else if (f3 == 0 && f7 == 0x20) {
                mn = "sub";
                value = m->x[rs1] - m->x[rs2];
            } else if (f3 == 7 && f7 == 0x00) {
                mn = "and";
                value = m->x[rs1] & m->x[rs2];
            } else if (f3 == 6 && f7 == 0x00) {
                mn = "or";
                value = m->x[rs1] | m->x[rs2];
            } else {
                fail_json(step, pc0, insn, "unsupported_r_type");
                return 1;
            }
            write_reg(m, rd, value);
            snprintf(event, sizeof event, "\"rd\":%" PRIu32 ",\"value\":%" PRIu32, rd, rd ? value : 0u);
            break;
        }
        case 0x13: {
            int64_t imm = imm_i(insn);
            uint32_t value = 0;
            if (f3 == 0) {
                mn = "addi";
                value = m->x[rs1] + (uint32_t)imm;
            } else if (f3 == 7) {
                mn = "andi";
                value = m->x[rs1] & (uint32_t)imm;
            } else if (f3 == 6) {
                mn = "ori";
                value = m->x[rs1] | (uint32_t)imm;
            } else {
                fail_json(step, pc0, insn, "unsupported_i_type");
                return 1;
            }
            write_reg(m, rd, value);
            snprintf(event, sizeof event, "\"rd\":%" PRIu32 ",\"value\":%" PRIu32 ",\"imm\":%" PRId64, rd, rd ? value : 0u, imm);
            break;
        }
        case 0x03: {
            int64_t imm = imm_i(insn);
            uint32_t addr = m->x[rs1] + (uint32_t)imm;
            if (f3 != 2) {
                fail_json(step, pc0, insn, "unsupported_load");
                return 1;
            }
            if (addr % 4u) {
                fail_json(step, pc0, insn, "misaligned_lw");
                return 1;
            }
            if (addr > MEM_SIZE - 4u) {
                fail_json(step, pc0, insn, "load_out_of_bounds");
                return 1;
            }
            mn = "lw";
            uint32_t value = load32le(&m->mem[addr]);
            write_reg(m, rd, value);
            snprintf(event, sizeof event, "\"rd\":%" PRIu32 ",\"value\":%" PRIu32 ",\"addr\":%" PRIu32, rd, rd ? value : 0u, addr);
            break;
        }
        case 0x23: {
            int64_t imm = imm_s(insn);
            uint32_t addr = m->x[rs1] + (uint32_t)imm;
            if (f3 != 2) {
                fail_json(step, pc0, insn, "unsupported_store");
                return 1;
            }
            if (addr % 4u) {
                fail_json(step, pc0, insn, "misaligned_sw");
                return 1;
            }
            if (addr > MEM_SIZE - 4u) {
                fail_json(step, pc0, insn, "store_out_of_bounds");
                return 1;
            }
            if (addr < m->text_words * 4u) {
                fail_json(step, pc0, insn, "store_to_text");
                return 1;
            }
            mn = "sw";
            store32le(&m->mem[addr], m->x[rs2]);
            snprintf(event, sizeof event, "\"addr\":%" PRIu32 ",\"value\":%" PRIu32, addr, m->x[rs2]);
            break;
        }
        case 0x63: {
            int64_t imm = imm_b(insn);
            bool take = false;
            if (f3 == 0) {
                mn = "beq";
                take = m->x[rs1] == m->x[rs2];
            } else if (f3 == 1) {
                mn = "bne";
                take = m->x[rs1] != m->x[rs2];
            } else if (f3 == 4) {
                mn = "blt";
                take = slt32(m->x[rs1], m->x[rs2]);
            } else if (f3 == 5) {
                mn = "bge";
                take = !slt32(m->x[rs1], m->x[rs2]);
            } else {
                fail_json(step, pc0, insn, "unsupported_branch");
                return 1;
            }
            if (take) next_pc = m->pc + (uint32_t)imm;
            if (next_pc % 4u || next_pc > m->text_words * 4u) {
                fail_json(step, pc0, insn, "branch_target_out_of_text");
                return 1;
            }
            snprintf(event, sizeof event, "\"taken\":%s,\"target\":%" PRIu32, take ? "true" : "false", next_pc);
            break;
        }
        default:
            fail_json(step, pc0, insn, "unsupported_opcode");
            return 1;
        }

        m->pc = next_pc;
        m->x[0] = 0;
        printf("{\"step\":%" PRIu32 ",\"pc\":%" PRIu32 ",\"inst\":\"0x%08" PRIx32 "\",\"op\":\"%s\",%s,\"next_pc\":%" PRIu32 ",\"x0\":%" PRIu32 "}\n",
               step, pc0, insn, mn, event, m->pc, m->x[0]);
    }
    fail_json(MAX_STEPS, m->pc, 0, "step_limit");
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s program.hex\n", argv[0]);
        return 2;
    }
    Machine m;
    memset(&m, 0, sizeof m);
    load_program(argv[1], &m);
    return run(&m);
}
