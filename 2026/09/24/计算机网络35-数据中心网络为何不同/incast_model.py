#!/usr/bin/env python3
"""Calculate an ECMP bucket map and a bounded synchronous-incast queue."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = json.loads((ROOT / "topology.json.txt").read_text(encoding="utf-8"))
    spines = config["topology"]["spines"]
    buckets = {spine: [] for spine in spines}
    for number in range(config["ecmp"]["flow_count"]):
        flow = f"10.0.1.{number + 1}:40000->10.0.2.99:443/TCP"
        index = hashlib.sha256(flow.encode("ascii")).digest()[0] % len(spines)
        buckets[spines[index]].append(flow)

    incast = config["incast"]
    service_us = incast["packet_bytes"] * 8 * 1_000_000 / incast["receiver_egress_bps"]
    cases = {}
    for senders in incast["sender_counts"]:
        packets = senders * incast["packets_per_sender"]
        cases[str(senders)] = {
            "total_packets": packets,
            "total_bytes": packets * incast["packet_bytes"],
            "packet_serialization_us": service_us,
            "last_packet_wait_us": (packets - 1) * service_us,
        }
    result = {
        "scope": "bounded static model; all packets arrive simultaneously",
        "ecmp_bucket_counts": {key: len(value) for key, value in buckets.items()},
        "ecmp_each_flow_uses_one_spine": sum(map(len, buckets.values())) == config["ecmp"]["flow_count"],
        "incast_cases": cases,
    }
    assert result["ecmp_each_flow_uses_one_spine"]
    assert cases["8"]["last_packet_wait_us"] > cases["1"]["last_packet_wait_us"]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
