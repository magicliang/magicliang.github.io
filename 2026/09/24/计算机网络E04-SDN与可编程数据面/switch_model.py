#!/usr/bin/env python3
"""Execute a deterministic teaching table with explicitly custom semantics."""

import argparse
import ipaddress
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CUSTOM_SELECTION = "highest numeric priority, then longest prefix, then input order"


def apply_table(address, rules):
    ip = ipaddress.ip_address(address)
    matches = [
        (index, rule)
        for index, rule in enumerate(rules)
        if ip in ipaddress.ip_network(rule["prefix"])
    ]
    if not matches:
        return {"rule": "table-miss", "action": "DROP"}

    highest_priority = max(rule["priority"] for _, rule in matches)
    highest = [(index, rule) for index, rule in matches if rule["priority"] == highest_priority]
    index, rule = max(
        highest,
        key=lambda item: (ipaddress.ip_network(item[1]["prefix"]).prefixlen, -item[0]),
    )
    result = {"rule": rule["name"], "action": rule["action"]}
    if len(highest) > 1:
        result["same_highest_priority"] = [candidate["name"] for _, candidate in highest]
        result["custom_tiebreak"] = "longest prefix, then input order"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "pipeline.json.txt").read_text(encoding="utf-8"))
    result = {
        "scope": "deterministic teaching model; not OpenFlow or P4 runtime evidence",
        "custom_selection": CUSTOM_SELECTION,
        "openflow_1_3_5_boundary": (
            "same-highest-priority overlapping matches: selected entry is undefined"
        ),
    }
    for version in ("before", "after"):
        result[version] = {address: apply_table(address, data[version]) for address in data["packets"]}
    counterexample = data["same_priority_overlap"]
    result["same_priority_counterexample"] = {
        "packet": counterexample["packet"],
        "custom_model_result": apply_table(counterexample["packet"], counterexample["rules"]),
    }
    assert result["before"]["10.0.0.42"]["action"] == "OUTPUT:1"
    assert result["after"]["10.0.0.42"]["action"] == "DROP"
    assert result["before"]["10.0.1.9"]["action"] == "OUTPUT:2"
    assert result["after"]["10.0.1.9"]["action"] == "OUTPUT:3"
    assert result["after"]["192.0.2.1"]["action"] == "DROP"
    tie_result = result["same_priority_counterexample"]["custom_model_result"]
    assert tie_result["same_highest_priority"] == ["broad-output", "host-drop"]
    assert tie_result["rule"] == "host-drop"
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
