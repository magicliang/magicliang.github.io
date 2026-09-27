#!/usr/bin/env python3
"""Execute a deterministic priority and longest-prefix match-action table."""

import argparse
import ipaddress
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def apply_table(address, rules):
    ip = ipaddress.ip_address(address)
    matches = [rule for rule in rules if ip in ipaddress.ip_network(rule["prefix"])]
    if not matches:
        return {"rule": "table-miss", "action": "DROP"}
    rule = max(matches, key=lambda item: (item["priority"], ipaddress.ip_network(item["prefix"]).prefixlen))
    return {"rule": rule["name"], "action": rule["action"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "pipeline.json.txt").read_text(encoding="utf-8"))
    result = {"scope": "software match-action model; not OpenFlow or P4 runtime evidence"}
    for version in ("before", "after"):
        result[version] = {address: apply_table(address, data[version]) for address in data["packets"]}
    assert result["before"]["10.0.0.42"]["action"] == "OUTPUT:1"
    assert result["after"]["10.0.0.42"]["action"] == "DROP"
    assert result["before"]["10.0.1.9"]["action"] == "OUTPUT:2"
    assert result["after"]["10.0.1.9"]["action"] == "OUTPUT:3"
    assert result["after"]["192.0.2.1"]["action"] == "DROP"
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
