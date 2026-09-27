#!/usr/bin/env python3
"""Deterministic five-tuple calculations for NAT and failure classification."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Flow:
    protocol: str
    source_address: str
    source_port: int
    destination_address: str
    destination_port: int

    def reverse(self) -> "Flow":
        return Flow(
            self.protocol,
            self.destination_address,
            self.destination_port,
            self.source_address,
            self.source_port,
        )


def snat(original: Flow, public_address: str, public_port: int) -> dict[str, Flow]:
    translated = Flow(
        original.protocol,
        public_address,
        public_port,
        original.destination_address,
        original.destination_port,
    )
    return {
        "original": original,
        "translated": translated,
        "reply_at_gateway": translated.reverse(),
        "reply_after_reverse_nat": original.reverse(),
    }


def dnat(original: Flow, internal_address: str, internal_port: int) -> dict[str, Flow]:
    translated = Flow(
        original.protocol,
        original.source_address,
        original.source_port,
        internal_address,
        internal_port,
    )
    return {
        "original": original,
        "translated": translated,
        "reply_at_gateway": translated.reverse(),
        "reply_after_reverse_nat": original.reverse(),
    }


def classify(route_exists: bool, filter_accepts: bool, state_alive: bool, needs_state: bool) -> str:
    if not route_exists:
        return "ROUTE_FAILURE"
    if needs_state and not state_alive:
        return "STATE_EXPIRED"
    if not filter_accepts:
        return "FILTER_DROP"
    return "FORWARD"


def serialise(mapping: dict[str, Flow]) -> dict[str, dict[str, object]]:
    return {name: asdict(flow) for name, flow in mapping.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calculate fixed SNAT/DNAT tuples and diagnostic branches.")
    return parser.parse_args()


def main() -> int:
    parse_args()
    outbound = Flow("TCP", "10.0.0.2", 49152, "203.0.113.9", 443)
    inbound = Flow("TCP", "192.0.2.44", 53000, "198.51.100.7", 8443)
    snat_mapping = snat(outbound, "198.51.100.7", 62001)
    dnat_mapping = dnat(inbound, "10.0.0.10", 443)

    diagnoses = {
        "route_missing": classify(False, True, True, False),
        "filter_rejects": classify(True, False, True, False),
        "reverse_state_expired": classify(True, True, False, True),
        "forwarded": classify(True, True, True, True),
    }
    assertions = {
        "snat_changes_only_source_endpoint": (
            snat_mapping["translated"].source_address == "198.51.100.7"
            and snat_mapping["translated"].source_port == 62001
            and snat_mapping["translated"].destination_address == outbound.destination_address
            and snat_mapping["translated"].destination_port == outbound.destination_port
        ),
        "snat_reply_restores_original_reverse": snat_mapping["reply_after_reverse_nat"] == outbound.reverse(),
        "dnat_changes_only_destination_endpoint": (
            dnat_mapping["translated"].destination_address == "10.0.0.10"
            and dnat_mapping["translated"].destination_port == 443
            and dnat_mapping["translated"].source_address == inbound.source_address
            and dnat_mapping["translated"].source_port == inbound.source_port
        ),
        "dnat_reply_restores_public_source": dnat_mapping["reply_after_reverse_nat"] == inbound.reverse(),
        "failure_classes_are_distinct": len(set(diagnoses.values())) == 4,
        "protocol_is_part_of_tuple": outbound != Flow("UDP", "10.0.0.2", 49152, "203.0.113.9", 443),
    }
    report = {
        "snat": serialise(snat_mapping),
        "dnat": serialise(dnat_mapping),
        "diagnoses": diagnoses,
        "assertions": assertions,
        "boundaries": [
            "static tuple calculation, not a Linux conntrack implementation",
            "no namespace, route, firewall, NAT rule, packet capture, or timeout was exercised",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
