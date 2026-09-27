#!/usr/bin/env python3
"""Build deterministic teaching snapshots from Service and EndpointSlice JSON."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def ready_backends(service, endpoint_slice):
    service_port = service["spec"]["ports"][0]
    slice_port = endpoint_slice["ports"][0]
    assert service_port["protocol"] == slice_port["protocol"] == "TCP"
    assert service_port["targetPort"] == slice_port["port"]
    return sorted(
        f"{endpoint['addresses'][0]}:{slice_port['port']}"
        for endpoint in endpoint_slice["endpoints"]
        if endpoint.get("conditions", {}).get("ready") is True
    )


def choose(flow, backends):
    if not backends:
        return None
    digest = hashlib.sha256(flow.encode("ascii")).digest()
    return backends[int.from_bytes(digest[:8], "big") % len(backends)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    service = load("service.json.txt")
    before = ready_backends(service, load("endpointslices-before.json.txt"))
    after = ready_backends(service, load("endpointslices-after.json.txt"))
    flow = "10.244.3.7:51000->10.96.0.10:80/TCP"
    result = {
        "scope": "deterministic teaching model; not a kube-proxy algorithm",
        "virtual_service": "10.96.0.10:80/TCP",
        "flow": flow,
        "before": {"ready_backends": before, "selected": choose(flow, before)},
        "after": {"ready_backends": after, "selected": choose(flow, after)},
        "assertions": {
            "before_has_two_ready_backends": len(before) == 2,
            "after_has_one_ready_backend": len(after) == 1,
            "terminating_backend_removed_from_new_selection": "10.244.1.21:8080" not in after,
        },
    }
    assert all(result["assertions"].values())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
