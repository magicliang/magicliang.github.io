#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
PAGE_SIZE = 4096
SUPERPAGE_SIZE = 4 * 1024 * 1024
PTE_SIZE = 4
R = 1 << 1
W = 1 << 2
X = 1 << 3
U = 1 << 4
A = 1 << 6
D = 1 << 7


@dataclass(frozen=True)
class Pte:
    ppn: int
    flags: int

    def valid(self) -> bool:
        return bool(self.flags & 1)

    def leaf(self) -> bool:
        return bool(self.flags & (R | W | X))

    def encode(self) -> int:
        return (self.ppn << 10) | self.flags


@dataclass(frozen=True)
class TlbEntry:
    va_base: int
    pa_base: int
    page_bytes: int
    flags: int

    def covers(self, va: int) -> bool:
        return self.va_base <= va < self.va_base + self.page_bytes

    def pa(self, va: int) -> int:
        return self.pa_base + (va - self.va_base)


@dataclass
class Hart:
    name: str
    tlb: dict[tuple[int, int], TlbEntry]


class DataCache:
    def __init__(self, capacity_bytes: int = 128, line_bytes: int = 64) -> None:
        self.line_count = capacity_bytes // line_bytes
        self.line_bytes = line_bytes
        self.lru: OrderedDict[int, None] = OrderedDict()

    def load(self, pa: int, label: str) -> dict[str, object]:
        tag = pa // self.line_bytes
        event = "data_cache_hit" if tag in self.lru else "data_cache_miss"
        if tag in self.lru:
            self.lru.move_to_end(tag)
        else:
            self.lru[tag] = None
            if len(self.lru) > self.line_count:
                self.lru.popitem(last=False)
        return {"event": event, "label": label, "pa": hex(pa), "line_bytes": self.line_bytes, "tag": hex(tag)}


class Sv32:
    def __init__(self) -> None:
        self.pt: dict[tuple[int, int], Pte] = {}
        self.traps: list[dict[str, object]] = []

    def map_table(self, vpn1: int, l0_ppn: int) -> None:
        self.pt[(1, vpn1)] = Pte(l0_ppn, 1)

    def map_leaf(self, vpn1: int, vpn0: int, ppn: int, flags: int) -> None:
        self.pt[(0, vpn1 << 10 | vpn0)] = Pte(ppn, flags | 1 | A | D)

    def map_superpage(self, vpn1: int, ppn: int, flags: int) -> None:
        self.pt[(1, vpn1)] = Pte(ppn, flags | 1 | A | D)

    def permission_fault(self, flags: int, access: str, mode: str, sum_enabled: bool) -> str | None:
        if flags & W and not flags & R:
            return "reserved_w_without_r"
        user_page = bool(flags & U)
        if mode == "U" and not user_page:
            return "user_to_supervisor_page"
        if mode == "S" and user_page and access == "fetch":
            return "supervisor_fetch_user_page"
        if mode == "S" and user_page and access in {"load", "store"} and not sum_enabled:
            return "supervisor_user_page_sum_clear"
        if access == "load" and not flags & R:
            return "load_without_read"
        if access == "store" and not flags & W:
            return "store_without_write"
        if access == "fetch" and not flags & X:
            return "fetch_without_execute"
        return None

    def tlb_lookup(self, hart: Hart, va: int) -> TlbEntry | None:
        vpn = va >> 12
        vpn1 = va >> 22
        return hart.tlb.get((PAGE_SIZE, vpn)) or hart.tlb.get((SUPERPAGE_SIZE, vpn1))

    def translate(self, hart: Hart, va: int, access: str, mode: str = "S", sum_enabled: bool = False) -> dict[str, object]:
        vpn1 = (va >> 22) & 0x3FF
        vpn0 = (va >> 12) & 0x3FF
        off = va & 0xFFF
        vpn = va >> 12
        entry = self.tlb_lookup(hart, va)
        if entry is not None:
            reason = self.permission_fault(entry.flags, access, mode, sum_enabled)
            if reason is not None:
                return self.fault(hart, va, access, reason, "tlb_cached_pte")
            return {"event": "tlb_hit", "hart": hart.name, "va": hex(va), "pa": hex(entry.pa(va)), "access": access, "mode": mode, "sum": sum_enabled, "page_bytes": entry.page_bytes}

        l1 = self.pt.get((1, vpn1))
        l1_addr = f"root + {vpn1} * {PTE_SIZE}"
        if l1 is None or not l1.valid():
            return self.fault(hart, va, access, "level1_invalid", l1_addr)
        if l1.leaf():
            if l1.ppn & 0x3FF:
                return self.fault(hart, va, access, "misaligned_superpage", l1_addr)
            reason = self.permission_fault(l1.flags, access, mode, sum_enabled)
            if reason is not None:
                return self.fault(hart, va, access, reason, l1_addr)
            va_base = vpn1 << 22
            pa_base = l1.ppn << 12
            hart.tlb[(SUPERPAGE_SIZE, vpn1)] = TlbEntry(va_base, pa_base, SUPERPAGE_SIZE, l1.flags)
            return {"event": "tlb_miss_superpage_walk", "hart": hart.name, "va": hex(va), "vpn1": hex(vpn1), "pte_addresses": [l1_addr], "pte": hex(l1.encode()), "pa": hex(pa_base | (vpn0 << 12) | off), "access": access, "mode": mode, "sum": sum_enabled, "page_bytes": SUPERPAGE_SIZE}

        l0 = self.pt.get((0, vpn1 << 10 | vpn0))
        l0_addr = hex(l1.ppn * PAGE_SIZE + vpn0 * PTE_SIZE)
        if l0 is None or not l0.valid() or not l0.leaf():
            return self.fault(hart, va, access, "level0_invalid_or_nonleaf", l0_addr)
        reason = self.permission_fault(l0.flags, access, mode, sum_enabled)
        if reason is not None:
            return self.fault(hart, va, access, reason, l0_addr)

        pa_page = l0.ppn * PAGE_SIZE
        hart.tlb[(PAGE_SIZE, vpn)] = TlbEntry(vpn << 12, pa_page, PAGE_SIZE, l0.flags)
        return {"event": "tlb_miss_page_walk", "hart": hart.name, "va": hex(va), "vpn": hex(vpn), "pte_addresses": [l1_addr, l0_addr], "pte": hex(l0.encode()), "pa": hex(pa_page | off), "access": access, "mode": mode, "sum": sum_enabled, "page_bytes": PAGE_SIZE}

    def fault(self, hart: Hart, va: int, access: str, reason: str, pte_address: str) -> dict[str, object]:
        trap = {"event": "page_fault", "hart": hart.name, "scause": f"{access}_page_fault", "stval": hex(va), "reason": reason, "pte_address": pte_address}
        self.traps.append(trap)
        return trap


def sfence_vma(hart: Hart, va: int | None = None) -> dict[str, object]:
    before = len(hart.tlb)
    if va is None:
        hart.tlb.clear()
    else:
        for key, entry in list(hart.tlb.items()):
            if entry.covers(va):
                del hart.tlb[key]
    return {"event": "sfence_vma_local", "hart": hart.name, "before": before, "after": len(hart.tlb), "va": None if va is None else hex(va)}


def cache_after_translation(cache: DataCache, event: dict[str, object], label: str) -> dict[str, object]:
    assert "pa" in event, event
    return cache.load(int(str(event["pa"]), 16), label)


def run() -> dict[str, object]:
    model = Sv32()
    hart0 = Hart("hart0", {})
    hart1 = Hart("hart1", {})
    cache = DataCache()
    va = 0x0040_1234
    vpn1 = (va >> 22) & 0x3FF
    vpn0 = (va >> 12) & 0x3FF
    model.map_table(vpn1, 0x200)
    model.map_leaf(vpn1, vpn0, 0x300, R | W)

    events: list[dict[str, object]] = []
    first_load = model.translate(hart0, va, "load")
    events.append(first_load)
    events.append(cache_after_translation(cache, first_load, "first_load_after_tlb_miss"))
    second_load = model.translate(hart0, va, "load")
    events.append(second_load)
    events.append(cache_after_translation(cache, second_load, "second_load_after_tlb_hit"))
    events.append(model.translate(hart0, va, "load", mode="U"))
    events.append(model.translate(hart0, va, "fetch"))
    events.append(model.translate(hart0, va, "store", mode="U"))

    ro_va = 0x0080_0004
    ro_vpn1 = (ro_va >> 22) & 0x3FF
    ro_vpn0 = (ro_va >> 12) & 0x3FF
    model.map_table(ro_vpn1, 0x210)
    model.map_leaf(ro_vpn1, ro_vpn0, 0x310, R)
    events.append(model.translate(hart0, ro_va, "store"))

    user_va = 0x0140_0010
    user_vpn1 = (user_va >> 22) & 0x3FF
    user_vpn0 = (user_va >> 12) & 0x3FF
    model.map_table(user_vpn1, 0x240)
    model.map_leaf(user_vpn1, user_vpn0, 0x340, R | W | X | U)
    events.append(model.translate(hart0, user_va, "load", mode="S", sum_enabled=False))
    events.append(model.translate(hart0, user_va, "load", mode="S", sum_enabled=True))
    events.append(model.translate(hart0, user_va, "store", mode="S", sum_enabled=True))
    events.append(model.translate(hart0, user_va, "fetch", mode="S"))

    super_va = 0x0180_0040
    super_vpn1 = (super_va >> 22) & 0x3FF
    model.map_superpage(super_vpn1, 0x3800, R | W | X)
    events.append(model.translate(hart0, super_va, "load"))
    events.append(model.translate(hart0, super_va + 0x2000, "load"))

    missing_va = 0x00C0_0008
    missing_vpn1 = (missing_va >> 22) & 0x3FF
    missing_vpn0 = (missing_va >> 12) & 0x3FF
    model.map_table(missing_vpn1, 0x220)
    events.append(model.translate(hart0, missing_va, "load"))
    model.map_leaf(missing_vpn1, missing_vpn0, 0x320, R | W)
    events.append(sfence_vma(hart0, missing_va))
    events.append(model.translate(hart0, missing_va, "load"))

    old_va = 0x0100_0000
    old_vpn1 = (old_va >> 22) & 0x3FF
    old_vpn0 = (old_va >> 12) & 0x3FF
    model.map_table(old_vpn1, 0x230)
    model.map_leaf(old_vpn1, old_vpn0, 0x330, R | W)
    events.append(model.translate(hart0, old_va, "load"))
    events.append(model.translate(hart1, old_va, "load"))
    model.map_leaf(old_vpn1, old_vpn0, 0x331, R | W)
    events.append(sfence_vma(hart0, old_va))
    events.append(model.translate(hart0, old_va, "load"))
    events.append(model.translate(hart1, old_va, "load"))

    remote = {"va": hex(old_va), "hart0_after_local_sfence": events[-2]["pa"], "hart1_without_remote_sfence": events[-1]["pa"]}
    assert events[0]["event"] == "tlb_miss_page_walk"
    assert events[1]["event"] == "data_cache_miss"
    assert events[2]["event"] == "tlb_hit"
    assert events[3]["event"] == "data_cache_hit"
    assert any(e.get("reason") == "user_to_supervisor_page" and e.get("pte_address") == "tlb_cached_pte" for e in events)
    assert any(e.get("reason") == "supervisor_user_page_sum_clear" for e in events)
    assert any(e.get("event") == "tlb_miss_page_walk" and e.get("mode") == "S" and e.get("sum") is True for e in events)
    assert any(e.get("reason") == "supervisor_fetch_user_page" and e.get("pte_address") == "tlb_cached_pte" for e in events)
    assert any(e.get("event") == "tlb_miss_superpage_walk" and e.get("page_bytes") == SUPERPAGE_SIZE for e in events)
    assert any(e.get("event") == "tlb_hit" and e.get("page_bytes") == SUPERPAGE_SIZE for e in events)
    assert remote["hart0_after_local_sfence"] == "0x331000"
    assert remote["hart1_without_remote_sfence"] == "0x330000"

    return {
        "evidence_level": "功能执行",
        "scope": "finite Sv32 page-table/TLB and tiny data-cache model; no real trap entry, no kernel, no hardware TLB",
        "page_size": PAGE_SIZE,
        "superpage_size": SUPERPAGE_SIZE,
        "events": events,
        "trap_count": len(model.traps),
        "remote_stale_translation": remote,
        "unsupported_features": ["MXR full matrix", "ASID/global entries", "PMP", "hardware A/D update", "concurrent page-table walk races"],
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = run()
    (OUT / "sv32_trace.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
