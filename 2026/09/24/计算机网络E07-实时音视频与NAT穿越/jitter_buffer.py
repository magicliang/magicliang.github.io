#!/usr/bin/env python3
"""Classify a fixed RTP-like arrival trace against playout deadlines."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "trace.json.txt").read_text(encoding="utf-8"))
    cases = {}
    for buffer_ms in data["buffer_ms"]:
        on_time = []
        late = []
        for packet in data["packets"]:
            deadline = packet["send_ms"] + buffer_ms
            target = on_time if packet["arrival_ms"] <= deadline else late
            target.append(packet["sequence"])
        cases[str(buffer_ms)] = {
            "on_time_sequences": on_time,
            "late_sequences": late,
            "scheduled_playout_delay_ms": buffer_ms,
        }
    assert len(cases["80"]["late_sequences"]) < len(cases["40"]["late_sequences"])
    assert cases["80"]["scheduled_playout_delay_ms"] > cases["40"]["scheduled_playout_delay_ms"]
    print(json.dumps({"scope": "static trace; synchronized clocks assumed", "cases": cases}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
