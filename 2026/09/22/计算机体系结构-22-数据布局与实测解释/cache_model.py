#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


class FullyAssocCache:
    def __init__(self, capacity_bytes: int, line_bytes: int) -> None:
        self.lines = capacity_bytes // line_bytes
        self.line_bytes = line_bytes
        self.lru: OrderedDict[int, None] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def touch(self, address: int) -> None:
        tag = address // self.line_bytes
        if tag in self.lru:
            self.hits += 1
            self.lru.move_to_end(tag)
            return
        self.misses += 1
        self.lru[tag] = None
        if len(self.lru) > self.lines:
            self.lru.popitem(last=False)


def simulate_aos_soa(n: int = 4096, line_bytes: int = 64, cache_bytes: int = 32768) -> dict[str, object]:
    point_size = 16
    aos = FullyAssocCache(cache_bytes, line_bytes)
    soa = FullyAssocCache(cache_bytes, line_bytes)
    for i in range(n):
        aos.touch(i * point_size)
        soa.touch(i * 4)
    return {
        "n": n,
        "line_bytes": line_bytes,
        "cache_bytes": cache_bytes,
        "aos_loads": n,
        "aos_misses": aos.misses,
        "soa_loads": n,
        "soa_misses": soa.misses,
        "interpretation": "reading one float from a 16-byte struct uses one line per 4 points; contiguous float array uses one line per 16 values",
    }


def simulate_block_working_set(n: int = 192, block: int = 32, elem_bytes: int = 4) -> dict[str, object]:
    plain_b_row_bytes = n * elem_bytes
    block_panel_bytes = block * block * elem_bytes
    return {
        "n": n,
        "block": block,
        "elem_bytes": elem_bytes,
        "plain_b_row_bytes": plain_b_row_bytes,
        "blocked_a_tile_bytes": block_panel_bytes,
        "blocked_b_tile_bytes": block_panel_bytes,
        "blocked_c_tile_bytes": block_panel_bytes,
        "three_tile_working_set_bytes": block_panel_bytes * 3,
        "scope": "working-set arithmetic only; not a cache-cycle simulator",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "evidence_level": "手算、功能执行",
        "aos_soa_model": simulate_aos_soa(),
        "blocking_model": simulate_block_working_set(),
    }
    (OUT / "cache_model.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
