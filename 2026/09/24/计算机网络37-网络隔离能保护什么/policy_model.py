#!/usr/bin/env python3
"""Evaluate network reachability separately from TLS hostname authentication."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "policy.json.txt").read_text(encoding="utf-8"))
    allowed = {tuple(edge) for edge in data["allow"]}
    results = []
    for case in data["cases"]:
        edge = (case["source"], case["target"], case["protocol"], case["port"])
        network_allowed = edge in allowed
        tls_applicable = case["port"] == 443 and case["requested_name"] is not None
        tls_identity_ok = tls_applicable and case["requested_name"] in case["certificate_names"]
        results.append({
            "name": case["name"],
            "network_allowed": network_allowed,
            "tls_applicable": tls_applicable,
            "tls_identity_ok": tls_identity_ok,
            "usable_authenticated_path": network_allowed and tls_identity_ok,
        })
    assert results[0]["usable_authenticated_path"]
    assert not results[1]["network_allowed"] and results[1]["tls_identity_ok"]
    assert not results[2]["network_allowed"] and not results[2]["tls_applicable"]
    assert results[3]["network_allowed"] and not results[3]["tls_identity_ok"]
    print(json.dumps({"scope": "static policy model", "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
