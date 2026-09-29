#!/usr/bin/env python3
"""Run a deterministic FIFO arrival-pattern model and print every event."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MODES = ("steady", "burst", "paced")


def validate_config(config: dict[str, Any]) -> None:
    positive_ints = ("packet_count", "service_time_us", "paced_group_size", "paced_interval_us")
    for key in positive_ints:
        if type(config.get(key)) is not int or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if type(config.get("jitter_max_us")) is not int or config["jitter_max_us"] < 0:
        raise ValueError("jitter_max_us must be a non-negative integer")
    seeds = config.get("seeds")
    if not isinstance(seeds, list) or not seeds or not all(type(seed) is int for seed in seeds):
        raise ValueError("seeds must be a non-empty integer list")


def arrivals(mode: str, config: dict[str, Any], seed: int) -> list[int]:
    rng = random.Random(seed)
    count = config["packet_count"]
    jitter = config["jitter_max_us"]
    if mode == "steady":
        return [index * config["service_time_us"] + rng.randint(0, jitter) for index in range(count)]
    if mode == "burst":
        return [rng.randint(0, jitter) for _ in range(count)]
    if mode == "paced":
        group = config["paced_group_size"]
        interval = config["paced_interval_us"]
        return [(index // group) * interval + rng.randint(0, jitter) for index in range(count)]
    raise ValueError(f"unknown mode: {mode}")


def events_for(times: list[int], service_time: int) -> list[dict[str, int]]:
    finish = 0
    events: list[dict[str, int]] = []
    for packet_id, arrival in sorted(enumerate(times), key=lambda item: (item[1], item[0])):
        start = max(arrival, finish)
        end = start + service_time
        queue_ahead = sum(1 for previous in events if previous["service_end_us"] > arrival)
        events.append(
            {
                "packet_id": packet_id,
                "arrival_us": arrival,
                "service_start_us": start,
                "service_end_us": end,
                "wait_us": start - arrival,
                "queue_ahead_at_arrival": queue_ahead,
            }
        )
        finish = end
    return events


def summarize(events: list[dict[str, int]]) -> dict[str, float | int]:
    waits = sorted(event["wait_us"] for event in events)
    nearest = lambda q: waits[math.ceil(q * len(waits)) - 1]
    return {
        "mean_wait_us": round(sum(waits) / len(waits), 3),
        "p50_wait_us": nearest(0.50),
        "p99_wait_us": nearest(0.99),
        "max_wait_us": max(waits),
    }


def check_event_arithmetic(events: list[dict[str, int]], service_time: int) -> bool:
    previous_end = 0
    for event in events:
        if event["service_start_us"] != max(event["arrival_us"], previous_end):
            return False
        if event["service_end_us"] != event["service_start_us"] + service_time:
            return False
        if event["wait_us"] != event["service_start_us"] - event["arrival_us"]:
            return False
        previous_end = event["service_end_us"]
    return True


def paced_batch_timeline(
    arrival_times: list[int], events: list[dict[str, int]], group_size: int
) -> list[dict[str, int | None]]:
    by_packet = {event["packet_id"]: event for event in events}
    batches = []
    previous_end: int | None = None
    for first_packet in range(0, len(arrival_times), group_size):
        packet_ids = range(first_packet, min(first_packet + group_size, len(arrival_times)))
        first_arrival = min(arrival_times[packet_id] for packet_id in packet_ids)
        last_service_end = max(by_packet[packet_id]["service_end_us"] for packet_id in packet_ids)
        overlap = None if previous_end is None else max(0, previous_end - first_arrival)
        batches.append(
            {
                "batch": first_packet // group_size + 1,
                "first_arrival_us": first_arrival,
                "previous_batch_end_us": previous_end,
                "overlap_us": overlap,
                "last_service_end_us": last_service_end,
            }
        )
        previous_end = last_service_end
    return batches


def evaluate_hypothesis(by_mode: dict[str, dict[str, Any]]) -> dict[str, Any]:
    observed = {mode: by_mode[mode]["summary"]["p99_wait_us"] for mode in MODES}
    holds = observed["burst"] > observed["paced"] > observed["steady"]
    return {
        "statement": "burst p99 > paced p99 > steady p99",
        "observed_p99_wait_us": observed,
        "supported_for_this_run": holds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = json.loads((ROOT / "experiment.json.txt").read_text(encoding="utf-8"))
    validate_config(config)
    runs = []
    for seed in config["seeds"]:
        by_mode = {}
        for mode in MODES:
            arrival_times = arrivals(mode, config, seed)
            events = events_for(arrival_times, config["service_time_us"])
            by_mode[mode] = {
                "events": events,
                "model_check": "PASS" if check_event_arithmetic(events, config["service_time_us"]) else "FAIL",
                "summary": summarize(events),
            }
            if mode == "paced":
                by_mode[mode]["batch_timeline"] = paced_batch_timeline(
                    arrival_times, events, config["paced_group_size"]
                )
        runs.append({"seed": seed, "hypothesis": evaluate_hypothesis(by_mode), "modes": by_mode})

    result = {
        "scope": "deterministic FIFO model; not a network performance experiment",
        "config": config,
        "model_checks": {
            "event_arithmetic": "PASS" if all(
                run["modes"][mode]["model_check"] == "PASS" for run in runs for mode in MODES
            ) else "FAIL",
            "meaning": "timestamps satisfy the declared FIFO equations; research hypothesis is reported separately",
        },
        "hypothesis_summary": {
            "statement": "burst p99 > paced p99 > steady p99",
            "supported_runs": sum(run["hypothesis"]["supported_for_this_run"] for run in runs),
            "total_runs": len(runs),
        },
        "runs": runs,
        "real_network_experiment": "NOT_RUN",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
