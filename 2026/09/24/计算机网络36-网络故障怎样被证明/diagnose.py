#!/usr/bin/env python3
"""Classify four fixed evidence records without inventing missing observations."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def classify(evidence):
    if evidence.get("dns_rcode") == "NXDOMAIN" and not evidence.get("connect_attempted"):
        return "DNS_RESPONSE"
    if evidence.get("dns_addresses") and evidence.get("syn_sent", 0) and not evidence.get("syn_ack_seen"):
        return "CONNECT_PATH"
    if evidence.get("tcp_established") and evidence.get("tls_error") and not evidence.get("http_bytes_seen"):
        return "TLS_IDENTITY"
    early = evidence.get("dns_ms", 0) + evidence.get("connect_ms", 0) + evidence.get("tls_ms", 0)
    if evidence.get("first_byte_ms", 0) > early * 10 and evidence.get("proxy_upstream_ms", 0) > early * 10:
        return "APPLICATION_OR_UPSTREAM"
    return "INSUFFICIENT_EVIDENCE"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    cases = json.loads((ROOT / "cases.json.txt").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        stage = classify(case["evidence"])
        assert stage == case["expected_stage"]
        assert case["excluded"]
        results.append({"name": case["name"], "stage": stage, "excluded": case["excluded"]})
    print(json.dumps({"scope": "synthetic evidence only", "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
