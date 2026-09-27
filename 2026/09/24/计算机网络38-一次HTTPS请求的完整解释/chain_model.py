#!/usr/bin/env python3
"""Validate a static baseline-fault-recovery matrix for an HTTPS chain."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "chain.json.txt").read_text(encoding="utf-8"))
    assert data["baseline"]["status"] == 200
    required = {"dns_error", "syn_loss", "pmtu_black_hole", "slow_backend"}
    names = {fault["name"] for fault in data["faults"]}
    assert names == required
    results = []
    for fault in data["faults"]:
        assert all(fault[key] for key in ("last_success", "failure", "excluded", "recovery"))
        results.append({
            "fault": fault["name"],
            "bounded_location": f"after {fault['last_success']}; at {fault['failure']}",
            "excluded": fault["excluded"],
            "recovery_check": fault["recovery"],
        })
    print(json.dumps({"scope": "static fault injection", "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
