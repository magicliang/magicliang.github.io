#!/usr/bin/env python3
"""Compare deterministic traffic and state costs for four delivery models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_INPUT = Path(__file__).with_name("scenario.json.txt")


def positive_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def calculate(data: dict[str, object]) -> dict[str, object]:
    object_mib = positive_int("object_mib", data.get("object_mib"))
    origin_hops = positive_int("origin_to_core_hops", data.get("origin_to_core_hops"))
    region_hops = positive_int("core_to_region_hops", data.get("core_to_region_hops"))
    receiver_hops = positive_int("region_to_receiver_hops", data.get("region_to_receiver_hops"))
    regions = positive_int("regions", data.get("regions"))
    receivers_per_region = positive_int("receivers_per_region", data.get("receivers_per_region"))

    receivers = regions * receivers_per_region
    source_to_region_hops = origin_hops + region_hops
    direct_copies = receivers * (source_to_region_hops + receiver_hops)
    multicast_copies = origin_hops + regions * region_hops + receivers * receiver_hops
    overlay_copies = regions * source_to_region_hops + receivers * receiver_hops
    warm_cache_copies = receivers * receiver_hops

    def traffic(link_copies: int, origin_copies: int) -> dict[str, int]:
        return {
            "link_object_copies": link_copies,
            "mib_link": link_copies * object_mib,
            "origin_object_copies": origin_copies,
        }

    return {
        "input": {
            **data,
            "receivers": receivers,
        },
        "state_inventory": {
            "application_overlay": {
                "overlay_sessions": regions + receivers,
                "relay_nodes": regions,
            },
            "direct_unicast": {"sender_delivery_relationships": receivers},
            "edge_cache": {
                "cached_object_copies": regions,
                "client_fetches": receivers,
            },
            "ip_multicast": {
                "modeled_group_forwarding_entries": 1 + regions,
                "receiver_memberships": receivers,
            },
        },
        "traffic": {
            "application_overlay": traffic(overlay_copies, regions),
            "direct_unicast": traffic(direct_copies, receivers),
            "edge_cache_cold": traffic(overlay_copies, regions),
            "edge_cache_warm": traffic(warm_cache_copies, 0),
            "ip_multicast": traffic(multicast_copies, 1),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as handle:
        data = json.load(handle)
    print(json.dumps(calculate(data), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
