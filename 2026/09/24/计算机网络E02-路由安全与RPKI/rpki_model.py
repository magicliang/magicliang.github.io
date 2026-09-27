#!/usr/bin/env python3
"""Perform offline route-origin validation and a separate local policy check."""

import argparse
import ipaddress
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def origin_state(route, roas):
    prefix = ipaddress.ip_network(route["prefix"])
    covering = [roa for roa in roas if prefix.subnet_of(ipaddress.ip_network(roa["prefix"]))]
    if not covering:
        return "NotFound"
    for roa in covering:
        if route["origin_as"] == roa["origin_as"] and prefix.prefixlen <= roa["max_length"]:
            return "Valid"
    return "Invalid"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "routes.json.txt").read_text(encoding="utf-8"))
    results = []
    for route in data["announcements"]:
        state = origin_state(route, data["roas"])
        results.append({
            "name": route["name"],
            "origin_state": state,
            "policy_permit": route["policy_permit"],
            "import": state != "Invalid" and route["policy_permit"],
        })
    by_name = {item["name"]: item for item in results}
    assert by_name["valid_origin"]["origin_state"] == "Valid"
    assert by_name["wrong_origin"]["origin_state"] == "Invalid"
    assert by_name["too_specific"]["origin_state"] == "Invalid"
    assert by_name["not_found"]["origin_state"] == "NotFound"
    assert by_name["valid_origin_but_leaked"]["origin_state"] == "Valid"
    assert not by_name["valid_origin_but_leaked"]["import"]
    print(json.dumps({"scope": "offline teaching policy", "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
