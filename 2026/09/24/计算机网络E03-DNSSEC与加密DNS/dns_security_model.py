#!/usr/bin/env python3
"""Separate DNS data authentication, hop encryption, and resolver visibility."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    cases = json.loads((ROOT / "cases.json.txt").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        encrypted = case["transport"] in {"DoT", "DoH"} and case["tls_identity_ok"]
        authenticated = case["dnssec_validation"] in {"stub", "recursive"}
        results.append({
            "name": case["name"],
            "dns_data_authenticated": authenticated,
            "stub_to_recursive_encrypted": encrypted,
            "recursive_sees_qname": True,
            "validation_point": case["dnssec_validation"],
        })
    assert results[0]["dns_data_authenticated"] and not results[0]["stub_to_recursive_encrypted"]
    assert results[1]["stub_to_recursive_encrypted"] and not results[1]["dns_data_authenticated"]
    assert results[2]["dns_data_authenticated"] and results[2]["recursive_sees_qname"]
    print(json.dumps({"scope": "static capability matrix", "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
