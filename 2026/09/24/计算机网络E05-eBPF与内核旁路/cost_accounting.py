#!/usr/bin/env python3
"""Audit packet conservation and cost fields in a synthetic path record."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "counters.json.txt").read_text(encoding="utf-8"))
    p = data["packets"]
    checks = {
        "driver_conservation": p["offered"] == p["driver_received"] + p["driver_drop"],
        "xdp_conservation": p["driver_received"] == p["redirected"] + p["xdp_drop"],
        "queue_conservation": p["redirected"] == p["userspace_received"] + p["queue_drop"],
        "processing_conservation": p["userspace_received"] == p["processed"],
        "tx_conservation": p["processed"] == p["transmitted"] + p["tx_drop"],
        "cpu_categories_present": set(data["cpu_seconds"]) == {"driver_and_irq", "xdp", "userspace"},
        "offload_state_recorded": set(data["offloads"]) == {"rx_checksum", "gro", "gso", "zero_copy_verified"},
    }
    assert all(checks.values())
    result = {
        "scope": data["scope"],
        "checks": checks,
        "accounted_drop_packets": p["driver_drop"] + p["xdp_drop"] + p["queue_drop"] + p["tx_drop"],
        "total_cpu_seconds": round(sum(data["cpu_seconds"].values()), 3),
        "zero_copy_claim_allowed": data["offloads"]["zero_copy_verified"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
