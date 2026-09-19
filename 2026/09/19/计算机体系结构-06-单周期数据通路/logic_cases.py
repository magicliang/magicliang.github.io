#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MASK4 = 0xF


def bit(value: int, index: int) -> int:
    return (value >> index) & 1


def full_adder(a: int, b: int, cin: int) -> tuple[int, int]:
    total = a + b + cin
    return total & 1, (total >> 1) & 1


def ripple_add(a: int, b: int, *, bits: int = 4, cin: int = 0) -> tuple[int, int]:
    carry = cin
    result = 0
    for index in range(bits):
        summed, carry = full_adder(bit(a, index), bit(b, index), carry)
        result |= summed << index
    return result & ((1 << bits) - 1), carry


def twos(value: int, *, bits: int = 4) -> int:
    sign = 1 << (bits - 1)
    mask = (1 << bits) - 1
    value &= mask
    return value - (1 << bits) if value & sign else value


def alu(a: int, b: int, op: str, *, bits: int = 4) -> tuple[int, dict[str, int]]:
    mask = (1 << bits) - 1
    if op == "ADD":
        y, carry = ripple_add(a, b, bits=bits)
    elif op == "SUB":
        y, carry = ripple_add(a, (~b) & mask, bits=bits, cin=1)
    elif op == "AND":
        y, carry = a & b, 0
    elif op == "OR":
        y, carry = a | b, 0
    elif op == "SLT":
        y, carry = 1 if twos(a, bits=bits) < twos(b, bits=bits) else 0, 0
    else:
        raise ValueError(op)
    return y & mask, {"zero": int((y & mask) == 0), "carry": carry}


@dataclass(frozen=True)
class PathDelay:
    name: str
    ps: int
    formula: str
    destination: str


CONTROL_ROWS = [
    ("add", "+4", "-", "-", "Reg", "Reg", "ADD", "Read", "1", "ALU"),
    ("sub", "+4", "-", "-", "Reg", "Reg", "SUB", "Read", "1", "ALU"),
    ("and", "+4", "-", "-", "Reg", "Reg", "AND", "Read", "1", "ALU"),
    ("or", "+4", "-", "-", "Reg", "Reg", "OR", "Read", "1", "ALU"),
    ("addi", "+4", "I", "-", "Reg", "Imm", "ADD", "Read", "1", "ALU"),
    ("andi", "+4", "I", "-", "Reg", "Imm", "AND", "Read", "1", "ALU"),
    ("ori", "+4", "I", "-", "Reg", "Imm", "OR", "Read", "1", "ALU"),
    ("lw", "+4", "I", "-", "Reg", "Imm", "ADD", "Read", "1", "Mem"),
    ("sw", "+4", "S", "-", "Reg", "Imm", "ADD", "Write", "0", "-"),
    ("beq taken", "ALU", "B", "-", "PC", "Imm", "ADD", "Read", "0", "-"),
    ("beq not taken", "+4", "B", "-", "PC", "Imm", "ADD", "Read", "0", "-"),
    ("bne taken", "ALU", "B", "-", "PC", "Imm", "ADD", "Read", "0", "-"),
    ("blt taken", "ALU", "B", "0", "PC", "Imm", "ADD", "Read", "0", "-"),
    ("bge taken", "ALU", "B", "0", "PC", "Imm", "ADD", "Read", "0", "-"),
]


DELAY_PS = {
    "clk_to_q_max": 35,
    "clk_to_q_min": 18,
    "setup": 25,
    "hold": 20,
    "min_combo": 10,
    "mux": 30,
    "alu_4bit": 160,
    "imem": 200,
    "control_rom": 80,
    "reg_read": 120,
    "imm_gen": 60,
    "alu_32bit": 220,
    "branch_cmp": 90,
    "dmem_read": 260,
    "dmem_write": 220,
    "wb_mux": 30,
    "pc_mux": 30,
}


def article05_reg_to_reg() -> PathDelay:
    ps = DELAY_PS["clk_to_q_max"] + DELAY_PS["mux"] + DELAY_PS["alu_4bit"] + DELAY_PS["setup"]
    return PathDelay(
        "article05_reg_to_reg_alu",
        ps,
        "clk_to_q_max + mux + alu_4bit + setup",
        "register",
    )


def add_path() -> PathDelay:
    inst = DELAY_PS["clk_to_q_max"] + DELAY_PS["imem"]
    regs = inst + DELAY_PS["reg_read"]
    control = inst + DELAY_PS["control_rom"]
    alu_in = max(regs, control) + DELAY_PS["mux"]
    result = alu_in + DELAY_PS["alu_32bit"]
    ps = max(result, control) + DELAY_PS["wb_mux"] + DELAY_PS["setup"]
    return PathDelay(
        "single_cycle_add",
        ps,
        "max(regs, control) + mux + alu_32bit; max(result, control) + wb_mux + setup",
        "rd",
    )


def lw_path() -> PathDelay:
    inst = DELAY_PS["clk_to_q_max"] + DELAY_PS["imem"]
    regs = inst + DELAY_PS["reg_read"]
    imm = inst + DELAY_PS["imm_gen"]
    control = inst + DELAY_PS["control_rom"]
    addr = max(regs, imm, control) + DELAY_PS["mux"] + DELAY_PS["alu_32bit"]
    mem = addr + DELAY_PS["dmem_read"]
    ps = max(mem, control) + DELAY_PS["wb_mux"] + DELAY_PS["setup"]
    return PathDelay(
        "single_cycle_lw",
        ps,
        "max(regs, imm, control) + mux + alu_32bit + dmem_read; max(mem, control) + wb_mux + setup",
        "rd",
    )


def sw_path() -> PathDelay:
    inst = DELAY_PS["clk_to_q_max"] + DELAY_PS["imem"]
    regs = inst + DELAY_PS["reg_read"]
    imm = inst + DELAY_PS["imm_gen"]
    control = inst + DELAY_PS["control_rom"]
    addr = max(regs, imm, control) + DELAY_PS["mux"] + DELAY_PS["alu_32bit"]
    ps = max(addr, regs, control) + DELAY_PS["dmem_write"]
    return PathDelay(
        "single_cycle_sw",
        ps,
        "addr=max(regs, imm, control)+mux+alu_32bit; max(addr, store_data, control)+dmem_write",
        "memory",
    )


def branch_path() -> PathDelay:
    inst = DELAY_PS["clk_to_q_max"] + DELAY_PS["imem"]
    regs = inst + DELAY_PS["reg_read"]
    imm = inst + DELAY_PS["imm_gen"]
    control = inst + DELAY_PS["control_rom"]
    target = max(DELAY_PS["clk_to_q_max"], imm, control) + DELAY_PS["mux"] + DELAY_PS["alu_32bit"]
    select = max(regs + DELAY_PS["branch_cmp"], control)
    pc_plus_4 = DELAY_PS["clk_to_q_max"] + DELAY_PS["alu_32bit"]
    ps = max(target, select, pc_plus_4) + DELAY_PS["pc_mux"] + DELAY_PS["setup"]
    return PathDelay(
        "single_cycle_branch_taken",
        ps,
        "max(target=PC/imm/control+mux+alu_32bit, select=max(regs+branch_cmp, control), pc_plus_4) + pc_mux + setup",
        "pc",
    )


def write_table(path: Path, header: list[str], rows: list[tuple[object, ...]]) -> None:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    adder_rows = []
    for a in (0, 1):
        for b in (0, 1):
            for cin in (0, 1):
                adder_rows.append((a, b, cin, *full_adder(a, b, cin)))

    sample_rows = []
    for a, b in [(0x3, 0x5), (0x7, 0x1), (0x8, 0x1), (0xF, 0x1), (0xA, 0x6)]:
        for op in ["ADD", "SUB", "AND", "OR", "SLT"]:
            y, flags = alu(a, b, op)
            sample_rows.append((f"0x{a:X}", f"0x{b:X}", op, f"0x{y:X}", flags["zero"], flags["carry"]))

    all_checks = 0
    for a in range(16):
        for b in range(16):
            assert alu(a, b, "ADD")[0] == (a + b) & MASK4
            assert alu(a, b, "SUB")[0] == (a - b) & MASK4
            assert alu(a, b, "AND")[0] == a & b
            assert alu(a, b, "OR")[0] == a | b
            assert alu(a, b, "SLT")[0] == int(twos(a) < twos(b))
            all_checks += 5

    write_table(OUT / "full_adder_truth_table.md", ["a", "b", "cin", "sum", "cout"], adder_rows)
    write_table(OUT / "alu_sample_table.md", ["a", "b", "op", "y", "zero", "carry"], sample_rows)
    write_table(
        OUT / "control_table.md",
        ["inst", "PCSel", "ImmSel", "BrUn", "ASel", "BSel", "ALUSel", "MemRW", "RegWEn", "WBSel"],
        CONTROL_ROWS,
    )

    paths = [article05_reg_to_reg(), add_path(), lw_path(), sw_path(), branch_path()]
    hold_lhs = DELAY_PS["clk_to_q_min"] + DELAY_PS["min_combo"]
    assert hold_lhs >= DELAY_PS["hold"]
    assert max(paths, key=lambda item: item.ps).name == "single_cycle_lw"

    write_table(
        OUT / "timing_report.md",
        ["path", "formula", "delay_ps", "destination"],
        [(p.name, p.formula, p.ps, p.destination) for p in paths],
    )

    summary = {
        "evidence_level": "手算、功能执行",
        "timing_scope": "static delay arithmetic with parallel arrival times, not cycle simulation",
        "alu_bits": 4,
        "alu_exhaustive_checks": all_checks,
        "control_rows": len(CONTROL_ROWS),
        "delays_ps": DELAY_PS,
        "hold_check": {
            "clk_to_q_plus_min_combo_ps": hold_lhs,
            "hold_ps": DELAY_PS["hold"],
            "passes": True,
        },
        "critical_path": max((p.__dict__ for p in paths), key=lambda item: item["ps"]),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    (OUT / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
