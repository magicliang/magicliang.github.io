#!/usr/bin/env python3
"""Validate a fixed CNI config and calculate VXLAN MTU budgets."""
import argparse
import json
from pathlib import Path


def mtu(underlay: int, outer_ip: int) -> dict[str, int]:
    outer_udp, vxlan, inner_eth = 8, 8, 14
    return {
        "underlay_l3_mtu": underlay,
        "outer_ip": outer_ip,
        "outer_udp": outer_udp,
        "vxlan": vxlan,
        "inner_ethernet": inner_eth,
        "max_inner_ethernet_frame": underlay - outer_ip - outer_udp - vxlan,
        "max_inner_ip_mtu": underlay - outer_ip - outer_udp - vxlan - inner_eth,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the article's CNI config and VXLAN arithmetic.")
    parser.parse_args()
    config_path = Path(__file__).with_name("cni-bridge.conflist.json.txt")
    config = json.loads(config_path.read_text())
    plugin = config["plugins"][0]
    ipv4, ipv6 = mtu(1500, 20), mtu(1500, 40)
    assertions = {
        "cni_version_is_1_1_0": config["cniVersion"] == "1.1.0",
        "bridge_and_ipam_are_fixed": plugin["type"] == "bridge" and plugin["ipam"]["type"] == "host-local",
        "subnet_and_default_route_exist": plugin["ipam"]["ranges"][0][0]["subnet"] == "10.22.0.0/24" and plugin["ipam"]["routes"][0]["dst"] == "0.0.0.0/0",
        "configured_mtu_matches_ipv4_vxlan_budget": plugin["mtu"] == ipv4["max_inner_ip_mtu"] == 1450,
        "ipv6_vxlan_budget_is_1430": ipv6["max_inner_ip_mtu"] == 1430,
    }
    report = {
        "cni": {"name": config["name"], "bridge": plugin["bridge"], "subnet": plugin["ipam"]["ranges"][0][0]["subnet"], "mtu": plugin["mtu"]},
        "same_host_path": ["container-eth0", "veth-container", "veth-host", "labbr0", "peer-veth"],
        "cross_host_vxlan_path": ["container-eth0", "veth", "bridge-or-route", "local-VTEP", "underlay", "remote-VTEP", "destination-veth"],
        "mtu": {"ipv4_underlay": ipv4, "ipv6_underlay": ipv6},
        "assertions": assertions,
        "boundaries": ["static configuration and arithmetic only", "no namespace, CNI plugin, VXLAN device, route, or packet capture was run"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
