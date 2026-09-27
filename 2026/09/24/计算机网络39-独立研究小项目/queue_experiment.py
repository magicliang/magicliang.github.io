#!/usr/bin/env python3
"""Run a deterministic FIFO arrival-pattern experiment and print raw waits."""

import argparse
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def arrivals(mode, config, seed):
    rng = random.Random(seed)
    count = config["packet_count"]
    jitter = config["jitter_max_us"]
    if mode == "steady":
        return [index * config["service_time_us"] + rng.randint(0, jitter) for index in range(count)]
    if mode == "burst":
        return [rng.randint(0, jitter) for _ in range(count)]
    group = config["paced_group_size"]
    interval = config["paced_interval_us"]
    return [(index // group) * interval + rng.randint(0, jitter) for index in range(count)]


def waits_for(times, service_time):
    finish = 0
    waits = []
    for arrival in sorted(times):
        start = max(arrival, finish)
        waits.append(start - arrival)
        finish = start + service_time
    return waits


def summarize(waits):
    ordered = sorted(waits)
    nearest = lambda q: ordered[math.ceil(q * len(ordered)) - 1]
    return {
        "mean_wait_us": round(sum(waits) / len(waits), 3),
        "p50_wait_us": nearest(0.50),
        "p99_wait_us": nearest(0.99),
        "max_wait_us": max(waits),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = json.loads((ROOT / "experiment.json.txt").read_text(encoding="utf-8"))
    runs = []
    for seed in config["seeds"]:
        by_mode = {}
        for mode in ("steady", "burst", "paced"):
            waits = waits_for(arrivals(mode, config, seed), config["service_time_us"])
            by_mode[mode] = {"raw_wait_us": waits, "summary": summarize(waits)}
        assert by_mode["burst"]["summary"]["p99_wait_us"] > by_mode["paced"]["summary"]["p99_wait_us"]
        assert by_mode["paced"]["summary"]["p99_wait_us"] > by_mode["steady"]["summary"]["p99_wait_us"]
        runs.append({"seed": seed, "modes": by_mode})
    print(json.dumps({"scope": "deterministic FIFO simulation", "config": config, "runs": runs}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
