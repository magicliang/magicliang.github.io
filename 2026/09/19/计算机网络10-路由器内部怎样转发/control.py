#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 control.py; retain chapter 07's sibling asset directory.
"""Compute and install immutable teaching routes; no real RIB/FIB or packets."""
import argparse
import json
import sys
from dataclasses import asdict, dataclass
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPENDENCIES = (HERE.parent / '2026-09-19-计算机网络07-IP地址怎样决定下一跳',
                HERE.parent / '计算机网络07-IP地址怎样决定下一跳', HERE)
SOURCE = next((path for path in DEPENDENCIES if (path / 'forwarder.py').is_file()), None)
if SOURCE is None:
    raise SystemExit('Keep chapter 07 forwarder.py in its sibling asset directory or beside this script')
sys.path.insert(0, str(SOURCE))
from forwarder import Decision, InvalidInput, Packet, Route, forward


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    route: Route
    cost: int

    def __post_init__(self) -> None:
        if not self.name or self.cost < 0:
            raise InvalidInput('candidate name must be nonempty and cost nonnegative')
        Packet(self.route.next_hop, 64)


@dataclass(frozen=True, slots=True)
class Table:
    version: int
    routes: tuple[Route, ...]


@dataclass(frozen=True, slots=True)
class Observation:
    stage: str
    candidates: tuple[Candidate, ...]
    computed: Table
    installed: Table
    decision: Decision


def compute(candidates: tuple[Candidate, ...], version: int) -> Table:
    """Per-prefix lowest cost is a teaching convention; equal costs are rejected."""
    if version < 1 or len({candidate.name for candidate in candidates}) != len(candidates):
        raise InvalidInput('version must be positive and candidate names must be unique')
    selected: list[Route] = []
    prefixes = sorted({candidate.route.prefix for candidate in candidates}, key=lambda prefix: (int(prefix.network_address), prefix.prefixlen))
    for prefix in prefixes:
        choices = sorted((candidate for candidate in candidates if candidate.route.prefix == prefix), key=lambda candidate: candidate.cost)
        if len(choices) > 1 and choices[0].cost == choices[1].cost:
            raise InvalidInput('equal lowest costs are unsupported; no ECMP or implicit tie-break')
        selected.append(choices[0].route)
    return Table(version, tuple(selected))


def demo(cost_a: int, cost_b: int) -> None:
    if not 0 <= cost_a < cost_b:
        raise InvalidInput('this scenario requires 0 <= cost-a < cost-b')
    prefix = IPv4Network('10.6.2.0/24')
    a = Candidate('A', Route(prefix, IPv4Address('192.0.2.1')), cost_a)
    b = Candidate('B', Route(prefix, IPv4Address('192.0.2.2')), cost_b)
    packet = Packet(IPv4Address('10.6.2.9'), 64)
    v1 = compute((a, b), 1)
    installed = v1
    initial = Observation('v1-installed', (a, b), v1, installed, forward(packet, installed.routes))
    assert initial.decision.next_hop == '192.0.2.1'
    v2 = compute((b,), 2)
    pending = Observation('A-withdrawn-v2-computed-only', (b,), v2, installed, forward(packet, installed.routes))
    assert pending.computed.version == 2 and pending.installed.version == 1
    assert pending.decision.next_hop == '192.0.2.1'
    installed = v2
    updated = Observation('v2-installed', (b,), v2, installed, forward(packet, installed.routes))
    assert updated.decision.next_hop == '192.0.2.2'
    expired = forward(Packet(packet.destination, 1), installed.routes)
    assert expired.error_kind == 'time-exceeded' and expired.icmp_error_allowed
    v3 = compute((), 3)
    installed = v3
    empty = Observation('all-withdrawn-v3-installed', (), v3, installed, forward(packet, installed.routes))
    assert empty.decision.error_kind == 'network-unreachable'
    for candidates in ((a, Candidate('C', b.route, cost_a)), (a, a)):
        try:
            compute(candidates, 4)
        except InvalidInput:
            continue
        raise AssertionError('ambiguous candidates were accepted')
    print(json.dumps({'scope': 'pure immutable teaching snapshots, no network or kernel programming',
                      'packet': asdict(packet),
                      'observations': [asdict(row) for row in (initial, pending, updated, empty)],
                      'ttl_one': asdict(expired), 'tie_and_duplicate_name_rejected': True},
                     default=str, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost-a', type=int, default=10)
    parser.add_argument('--cost-b', type=int, default=20)
    args = parser.parse_args()
    try:
        demo(args.cost_a, args.cost_b)
    except InvalidInput as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
