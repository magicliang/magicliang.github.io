#!/usr/bin/env python3
"""Evaluate ECN, PFC, and overflow in a bounded priority-queue model."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "queue.json.txt").read_text(encoding="utf-8"))
    queue = 0
    events = []
    for step, arrivals in enumerate(data["arrivals_per_step"]):
        offered = queue + arrivals
        marked = offered >= data["ecn_threshold_packets"]
        paused = offered >= data["pfc_threshold_packets"]
        dropped = max(0, offered - data["capacity_packets"])
        admitted = min(offered, data["capacity_packets"])
        served = min(admitted, data["service_packets_per_step"])
        queue = admitted - served
        events.append({"step": step, "arrivals": arrivals, "ecn_mark": marked, "pfc_pause": paused, "drop": dropped, "queue_after_service": queue})
    result = {
        "scope": "static single-priority queue; not an RDMA device result",
        "events": events,
        "same_priority_flows_paused_together": data["same_priority_flows"],
        "observed_ecn": any(event["ecn_mark"] for event in events),
        "observed_pfc": any(event["pfc_pause"] for event in events),
        "observed_drop_despite_threshold": any(event["drop"] for event in events),
    }
    assert result["observed_ecn"] and result["observed_pfc"] and result["observed_drop_despite_threshold"]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
