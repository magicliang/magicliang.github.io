#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 forwarder.py --demo
"""Pure IPv4 forwarding decisions; no packet serialization or network I/O."""
import argparse
import json
from dataclasses import asdict, dataclass
from ipaddress import IPv4Address, IPv4Network


@dataclass(frozen=True, slots=True)
class InvalidInput(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class Route:
    prefix: IPv4Network
    next_hop: IPv4Address


@dataclass(frozen=True, slots=True)
class Packet:
    destination: IPv4Address
    ttl: int
    icmp_error: bool = False
    link_broadcast: bool = False
    fragment_offset: int = 0

    def __post_init__(self) -> None:
        address = self.destination
        if (address.is_multicast or address.is_loopback or address.is_unspecified
                or address.is_reserved or address in IPv4Network('0.0.0.0/8')
                or address.is_link_local):
            raise InvalidInput('destination must be an ordinary unicast IPv4 address')
        if not 0 <= self.ttl <= 255 or not 0 <= self.fragment_offset <= 8191:
            raise InvalidInput('TTL must be 0..255; fragment offset must be 0..8191')


@dataclass(frozen=True, slots=True)
class Decision:
    action: str
    matched_prefix: str | None = None
    next_hop: str | None = None
    outgoing_ttl: int | None = None
    error_kind: str | None = None
    icmp_error_allowed: bool = False


def forward(packet: Packet, routes: tuple[Route, ...]) -> Decision:
    """Validate table, test TTL, then longest-prefix lookup; never emit ICMP."""
    if len({route.prefix for route in routes}) != len(routes):
        raise InvalidInput('duplicate prefix: ECMP and preference are outside this model')
    allowed = not (packet.icmp_error or packet.link_broadcast or packet.fragment_offset > 0)
    if packet.ttl <= 1:
        return Decision('drop', error_kind='time-exceeded', icmp_error_allowed=allowed)
    matches = [route for route in routes if packet.destination in route.prefix]
    if not matches:
        return Decision('drop', error_kind='network-unreachable', icmp_error_allowed=allowed)
    selected = max(matches, key=lambda route: route.prefix.prefixlen)
    return Decision('forward', str(selected.prefix), str(selected.next_hop), packet.ttl - 1)


def demo() -> None:
    routes = tuple(Route(IPv4Network(prefix), IPv4Address(hop)) for prefix, hop in (
        ('0.0.0.0/0', '192.0.2.1'), ('10.0.0.0/8', '192.0.2.2'),
        ('10.6.0.0/16', '192.0.2.3'), ('10.6.2.0/24', '192.0.2.4'),
        ('10.6.2.9/32', '192.0.2.5')))
    cases: list[dict[str, str | int | bool | None]] = []
    for destination, prefix in (('192.0.2.1', '0.0.0.0/0'), ('10.9.0.1', '10.0.0.0/8'),
                                ('10.6.3.1', '10.6.0.0/16'), ('10.6.2.10', '10.6.2.0/24'),
                                ('10.6.2.9', '10.6.2.9/32')):
        result = forward(Packet(IPv4Address(destination), 64), routes)
        assert result.matched_prefix == prefix and result.outgoing_ttl == 63
        cases.append({'destination': destination, **asdict(result)})
    missing = forward(Packet(IPv4Address('192.0.2.1'), 64), routes[1:])
    assert missing.error_kind == 'network-unreachable' and missing.icmp_error_allowed
    first = forward(Packet(IPv4Address('10.6.2.9'), 2), routes)
    assert first.outgoing_ttl == 1
    second = forward(Packet(IPv4Address('10.6.2.9'), first.outgoing_ttl), routes)
    assert second.error_kind == 'time-exceeded' and second.icmp_error_allowed
    suppressed: list[dict[str, str | bool | int | None]] = []
    for ttl in (1, 64):
        for packet in (Packet(IPv4Address('192.0.2.1'), ttl, icmp_error=True),
                       Packet(IPv4Address('192.0.2.1'), ttl, link_broadcast=True),
                       Packet(IPv4Address('192.0.2.1'), ttl, fragment_offset=1)):
            result = forward(packet, ())
            assert result.action == 'drop' and not result.icmp_error_allowed
            suppressed.append({'ttl': ttl, 'icmp_error': packet.icmp_error,
                               'link_broadcast': packet.link_broadcast,
                               'fragment_offset': packet.fragment_offset, **asdict(result)})
    try:
        forward(Packet(IPv4Address('10.6.2.9'), 64), routes + (routes[0],))
    except InvalidInput:
        duplicate_rejected = True
    else:
        raise AssertionError('duplicate prefix accepted')
    rejected: list[str] = []
    for destination in ('0.1.2.3', '127.0.0.1', '224.0.0.1', '255.255.255.255', '169.254.1.2'):
        try:
            Packet(IPv4Address(destination), 64)
        except InvalidInput:
            rejected.append(destination)
        else:
            raise AssertionError('unsupported address accepted')
    print(json.dumps({'scope': 'pure decision model; fixed valid source 192.0.2.100; no network I/O',
                      'order': ['validate input/table', 'TTL', 'longest prefix'],
                      'matches': cases, 'no_route': asdict(missing),
                      'ttl_path': [asdict(first), asdict(second)],
                      'suppressed_errors': suppressed, 'duplicate_rejected': duplicate_rejected,
                      'rejected_destinations': rejected}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='run deterministic assertion examples')
    parser.add_argument('--destination', default='192.0.2.1')
    parser.add_argument('--ttl', type=int, default=64)
    args = parser.parse_args()
    try:
        packet = Packet(IPv4Address(args.destination), args.ttl)
        if args.demo:
            demo()
        else:
            print(json.dumps(asdict(forward(packet, ())), indent=2))
    except (InvalidInput, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
