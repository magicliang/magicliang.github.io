#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py (inside an owned Linux VM)
"""Observe gateway NDP before an isolated IPv6 UDP echo; static addresses only."""
import argparse
import json
import os
import platform
import select
import socket
import subprocess
import sys
import time
import uuid
from ipaddress import IPv6Address
from pathlib import Path
from typing import Final, assert_never

PAYLOAD: Final = b'net08-owned-udp-echo'
ROUTER_MAC: Final = bytes.fromhex('020000000801')


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout


def server() -> None:
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as udp:
        udp.bind(('2001:db8:8:2::2', 46008))
        udp.settimeout(5)
        print('READY', flush=True)
        data, peer = udp.recvfrom(65535)
        sent = udp.sendto(data, peer)
        assert sent == len(data)
        print(json.dumps({'server_received_hex': data.hex(), 'peer': peer}), flush=True)


def probe() -> None:
    # Capture is bound before the send; a few frames fit in its receive buffer.
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as capture:
        capture.bind(('eth0', 0))
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as udp:
            udp.bind(('2001:db8:8:1::2', 0))
            udp.settimeout(5)
            sent = udp.sendto(PAYLOAD, ('2001:db8:8:2::2', 46008))
            echoed, peer = udp.recvfrom(65535)
            assert sent == len(PAYLOAD) and echoed == PAYLOAD
            assert peer[:2] == ('2001:db8:8:2::2', 46008)
        frames: list[bytes] = []
        while select.select([capture], [], [], 0)[0]:
            frames.append(capture.recv(65535))
    # Fixed offsets: untagged Ethernet + IPv6 without extension headers only.
    requests = [frame for frame in frames if len(frame) >= 78
                and frame[12:14] == b'\x86\xdd' and frame[20] == 58 and frame[54] == 135]
    replies = [frame for frame in frames if len(frame) >= 78
               and frame[12:14] == b'\x86\xdd' and frame[20] == 58 and frame[54] == 136]
    outbound = [frame for frame in frames if len(frame) >= 62
                and frame[12:14] == b'\x86\xdd' and frame[20] == 17
                and frame[38:54] == socket.inet_pton(socket.AF_INET6, '2001:db8:8:2::2')]
    gateway = socket.inet_pton(socket.AF_INET6, 'fe80::1')
    assert requests and all(frame[62:78] == gateway for frame in requests)
    assert replies and any(frame[62:78] == gateway for frame in replies)
    assert outbound and all(frame[:6] == ROUTER_MAC for frame in outbound)
    print(json.dumps({'echo_hex': echoed.hex(), 'peer': peer,
                      'ns_targets': [socket.inet_ntop(socket.AF_INET6, frame[62:78]) for frame in requests],
                      'na_targets': [socket.inet_ntop(socket.AF_INET6, frame[62:78]) for frame in replies],
                      'outbound_ip_targets': [socket.inet_ntop(socket.AF_INET6, frame[38:54]) for frame in outbound],
                      'outbound_ethernet_targets': [frame[:6].hex(':') for frame in outbound],
                      'raw_frames': [frame.hex() for frame in frames]}), flush=True)


def lab() -> None:
    if platform.system() != 'Linux' or os.geteuid() != 0:
        raise SystemExit('Requires root inside an owned Linux VM; no host network changes')
    prefix = 'net08-' + uuid.uuid4().hex[:8]
    a, router, b = [prefix + '-' + suffix for suffix in ('a', 'r', 'b')]
    owned: list[str] = []
    children: list[subprocess.Popen[str]] = []
    script = str(Path(__file__).resolve())
    try:
        for namespace in (a, router, b):
            command('ip', 'netns', 'add', namespace)
            owned.append(namespace)
            command('ip', '-n', namespace, 'link', 'set', 'lo', 'up')
        for namespace, side, subnet in ((a, 'left', '1'), (b, 'right', '2')):
            command('ip', '-n', router, 'link', 'add', side, 'type', 'veth', 'peer', 'name', 'ep')
            command('ip', '-n', router, 'link', 'set', 'ep', 'netns', namespace)
            command('ip', '-n', namespace, 'link', 'set', 'ep', 'name', 'eth0')
            command('ip', '-n', router, 'link', 'set', side, 'addrgenmode', 'none')
            command('ip', '-n', namespace, 'link', 'set', 'eth0', 'addrgenmode', 'none')
            if side == 'left':
                command('ip', '-n', router, 'link', 'set', side, 'address', ROUTER_MAC.hex(':'))
            command('ip', '-n', router, '-6', 'address', 'add', f'2001:db8:8:{subnet}::1/64', 'dev', side)
            command('ip', '-n', namespace, '-6', 'address', 'add', f'2001:db8:8:{subnet}::2/64', 'dev', 'eth0')
            command('ip', '-n', router, '-6', 'address', 'add', 'fe80::1/64', 'dev', side)
            command('ip', '-n', namespace, '-6', 'address', 'add', 'fe80::2/64', 'dev', 'eth0')
            command('ip', '-n', router, 'link', 'set', side, 'up')
            command('ip', '-n', namespace, 'link', 'set', 'eth0', 'up')
            command('ip', '-n', namespace, '-6', 'route', 'add', 'default', 'via', 'fe80::1', 'dev', 'eth0')
        forwarding = command('ip', 'netns', 'exec', router, 'sysctl', '-w', 'net.ipv6.conf.all.forwarding=1')
        deadline = time.monotonic() + 10
        while True:
            addresses = {namespace: json.loads(command('ip', '-n', namespace, '-j', '-6', 'address', 'show'))
                         for namespace in owned}
            rows = [address for interfaces in addresses.values() for interface in interfaces
                    for address in interface['addr_info']]
            assert not any(row.get('dadfailed', False) for row in rows), 'DAD failed'
            if not any(row.get('tentative', False) for row in rows):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('IPv6 DAD did not finish within ten seconds')
            time.sleep(0.05)
        print(json.dumps({'addresses_after_dad': addresses, 'dad': 'enabled; waited until tentative cleared'}), flush=True)
        command('ip', '-n', a, '-6', 'neigh', 'flush', 'dev', 'eth0')
        print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                          'ip': command('ip', '-V').strip(), 'prefix': prefix,
                          'configuration': 'static IPv6, manual link-local addresses, no RA/SLAAC/DHCPv6',
                          'router_namespace_forwarding': forwarding.strip()}), flush=True)
        before = json.loads(command('ip', '-n', a, '-j', '-6', 'neigh', 'show', 'dev', 'eth0', 'nud', 'all'))
        route = json.loads(command('ip', '-n', a, '-j', '-6', 'route', 'get', '2001:db8:8:2::2'))
        after_query = json.loads(command('ip', '-n', a, '-j', '-6', 'neigh', 'show', 'dev', 'eth0', 'nud', 'all'))
        assert route[0]['gateway'] == 'fe80::1' and route[0]['dev'] == 'eth0'
        print(json.dumps({'neigh_before': before, 'route_get': route, 'neigh_after_route_get': after_query}), flush=True)
        assert not any(not IPv6Address(row['dst']).is_multicast for row in before)
        assert not any(not IPv6Address(row['dst']).is_multicast for row in after_query)
        proc = subprocess.Popen(['ip', 'netns', 'exec', b, sys.executable, script, 'server'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        children.append(proc)
        assert proc.stdout is not None
        if not select.select([proc.stdout], [], [], 5)[0] or proc.stdout.readline().strip() != 'READY':
            raise TimeoutError('UDP server did not become ready')
        observed = command('ip', 'netns', 'exec', a, sys.executable, script, 'probe')
        print(observed.strip(), flush=True)
        stdout, stderr = proc.communicate(timeout=5)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, proc.args, stderr=stderr)
        print(stdout.strip(), flush=True)
        after = json.loads(command('ip', '-n', a, '-j', '-6', 'neigh', 'show', 'dev', 'eth0', 'nud', 'all'))
        unicast_after = [row for row in after if not IPv6Address(row['dst']).is_multicast]
        assert len(unicast_after) == 1 and unicast_after[0]['dst'] == 'fe80::1'
        assert unicast_after[0]['lladdr'] == ROUTER_MAC.hex(':')
        print(json.dumps({'neigh_after_echo': after, 'unicast_neigh_after_echo': unicast_after, 'result': 'isolated cross-subnet UDP echo passed',
                          'scope': 'Linux veth IPv6 routing and NDP only; no RA/SLAAC/DHCPv6, physical network or public E2E'}), flush=True)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
        for namespace in reversed(owned):
            command('ip', 'netns', 'delete', namespace)
        remaining = command('ip', 'netns', 'list')
        assert not any(namespace in remaining for namespace in owned)
        print(json.dumps({'cleanup': 'only namespaces created by this run deleted', 'owned': owned}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['lab', 'server', 'probe'], nargs='?', default='lab')
    args = parser.parse_args()
    match args.mode:
        case 'lab':
            lab()
        case 'server':
            server()
        case 'probe':
            probe()
        case _:
            assert_never(args.mode)


if __name__ == '__main__':
    main()
