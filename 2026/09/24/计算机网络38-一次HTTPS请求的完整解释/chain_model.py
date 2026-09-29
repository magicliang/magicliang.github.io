#!/usr/bin/env python3
"""Check a synthetic HTTPS-chain case table and evaluate its finite PMTU model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPECTED_CASES = {"dns_error", "syn_loss", "pmtu_black_hole", "slow_backend"}
CASE_LIST_FIELDS = (
    "observable_evidence",
    "still_possible",
    "excluded_if",
    "recovery_criteria",
)


def require_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string")
    return value


def require_string_list(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{location} must be a non-empty list")
    for index, item in enumerate(value):
        require_nonempty_string(item, f"{location}[{index}]")
    return value


def validate_case_table(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise ValueError("document root must be an object")
    baseline = data.get("baseline")
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be an object")
    require_nonempty_string(baseline.get("host"), "baseline.host")
    require_nonempty_string(baseline.get("address"), "baseline.address")
    status = baseline.get("status")
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("baseline.status must be an HTTP status integer")

    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    if not all(isinstance(case, dict) for case in cases):
        raise ValueError("each case must be an object")
    names = {require_nonempty_string(case.get("name"), "case.name") for case in cases}
    if names != EXPECTED_CASES or len(cases) != len(EXPECTED_CASES):
        raise ValueError(f"case names must be exactly {sorted(EXPECTED_CASES)}")
    for case in cases:
        name = case["name"]
        require_nonempty_string(case.get("assumed_input"), f"{name}.assumed_input")
        for field in CASE_LIST_FIELDS:
            require_string_list(case.get(field), f"{name}.{field}")
    return cases


def evaluate_pmtu_model(model: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(model, dict):
        raise ValueError("pmtu_model must be an object")
    path_mtu = model.get("path_mtu_bytes")
    probes = model.get("ipv4_packet_sizes_bytes")
    if type(path_mtu) is not int or path_mtu <= 0:
        raise ValueError("pmtu_model.path_mtu_bytes must be positive")
    if not isinstance(probes, list) or not probes or not all(type(size) is int and size > 0 for size in probes):
        raise ValueError("pmtu_model.ipv4_packet_sizes_bytes must be a non-empty positive-integer list")
    dont_fragment = model.get("dont_fragment")
    icmp_delivered = model.get("icmp_fragmentation_needed_delivered")
    if not isinstance(dont_fragment, bool) or not isinstance(icmp_delivered, bool):
        raise ValueError("pmtu_model flags must be booleans")

    decisions = []
    for packet_size in probes:
        if packet_size <= path_mtu:
            outcome = "FORWARDED"
            calculation = f"{packet_size} <= {path_mtu}"
        elif not dont_fragment:
            outcome = "FRAGMENTATION_ALLOWED_IN_THIS_TOY_MODEL"
            calculation = f"{packet_size} > {path_mtu}; DF=false"
        elif icmp_delivered:
            outcome = "DROPPED_WITH_ICMP_FEEDBACK"
            calculation = f"{packet_size} > {path_mtu}; DF=true; ICMP delivered"
        else:
            outcome = "DROPPED_WITHOUT_FEEDBACK"
            calculation = f"{packet_size} > {path_mtu}; DF=true; ICMP suppressed"
        decisions.append(
            {"ipv4_packet_size_bytes": packet_size, "calculation": calculation, "outcome": outcome}
        )
    return {
        "assumptions": {
            "size_meaning": "complete IPv4 packet size",
            "path_mtu_bytes": path_mtu,
            "dont_fragment": dont_fragment,
            "icmp_fragmentation_needed_delivered": icmp_delivered,
        },
        "decisions": decisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = json.loads((ROOT / "chain.json.txt").read_text(encoding="utf-8"))
    cases = validate_case_table(data)
    result = {
        "scope": "synthetic case walkthrough and schema check; no service chain executed",
        "schema_check": {
            "status": "PASS",
            "meaning": "required fields and types are present; diagnostic correctness is not proven",
            "case_count": len(cases),
            "case_names": sorted(case["name"] for case in cases),
            "required_case_fields": ["assumed_input", *CASE_LIST_FIELDS],
        },
        "pmtu_finite_model": evaluate_pmtu_model(data["pmtu_model"]),
        "real_fault_injection": "NOT_RUN",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
