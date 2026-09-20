#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py (inside an owned Linux VM)
"""Observe gateway ARP before an isolated two-subnet UDP echo; no DHCP lease."""
import argparse
import json
import os
import platform
import select
import socket
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Final, assert_never

PAYLOAD: Final = b'net06-owned-udp-echo'
ROUTER_MAC: Final = bytes.fromhex('020000000601')


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout


def server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.bind(('10.6.2.2', 46006))
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
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind(('10.6.1.2', 0))
            udp.settimeout(5)
            sent = udp.sendto(PAYLOAD, ('10.6.2.2', 46006))
            echoed, peer = udp.recvfrom(65535)
            assert sent == len(PAYLOAD) and echoed == PAYLOAD
            assert peer == ('10.6.2.2', 46006)
        frames: list[bytes] = []
        while select.select([capture], [], [], 0)[0]:
            frames.append(capture.recv(65535))
    # These fixed offsets apply only to this untagged Ethernet/IPv4 experiment.
    requests = [frame for frame in frames if len(frame) >= 42
                and frame[12:14] == b'\x08\x06' and frame[20:22] == b'\x00\x01'
                and frame[28:32] == socket.inet_aton('10.6.1.2')]
    outbound = [frame for frame in frames if len(frame) >= 34
                and frame[12:14] == b'\x08\x00' and frame[30:34] == socket.inet_aton('10.6.2.2')]
    assert requests and all(frame[38:42] == socket.inet_aton('10.6.1.1') for frame in requests)
    assert outbound and all(frame[:6] == ROUTER_MAC for frame in outbound)
    print(json.dumps({'echo_hex': echoed.hex(), 'peer': peer,
                      'arp_request_targets': [socket.inet_ntoa(frame[38:42]) for frame in requests],
                      'outbound_ip_targets': [socket.inet_ntoa(frame[30:34]) for frame in outbound],
                      'outbound_ethernet_targets': [frame[:6].hex(':') for frame in outbound],
                      'raw_frames': [frame.hex() for frame in frames]}), flush=True)


def lab() -> None:
    if platform.system() != 'Linux' or os.geteuid() != 0:
        raise SystemExit('Requires root inside an owned Linux VM; no host network changes')
    prefix = 'net06-' + uuid.uuid4().hex[:8]
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
            command('ip', '-n', router, 'address', 'add', f'10.6.{subnet}.1/24', 'dev', side)
            command('ip', '-n', namespace, 'address', 'add', f'10.6.{subnet}.2/24', 'dev', 'eth0')
            command('ip', '-n', router, 'link', 'set', side, 'up')
            command('ip', '-n', namespace, 'link', 'set', 'eth0', 'up')
            command('ip', '-n', namespace, 'route', 'add', 'default', 'via', f'10.6.{subnet}.1')
        command('ip', '-n', router, 'link', 'set', 'left', 'address', ROUTER_MAC.hex(':'))
        forwarding = command('ip', 'netns', 'exec', router, 'sysctl', '-w', 'net.ipv4.ip_forward=1')
        print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                          'ip': command('ip', '-V').strip(), 'prefix': prefix,
                          'configuration': 'static IPv4, no DHCP client/server',
                          'router_namespace_forwarding': forwarding.strip()}), flush=True)
        before = json.loads(command('ip', '-n', a, '-j', '-4', 'neigh', 'show', 'dev', 'eth0', 'nud', 'all'))
        route = json.loads(command('ip', '-n', a, '-j', '-4', 'route', 'get', '10.6.2.2'))
        after_query = json.loads(command('ip', '-n', a, '-j', '-4', 'neigh', 'show', 'dev', 'eth0', 'nud', 'all'))
        assert before == [] and after_query == []
        assert route[0]['gateway'] == '10.6.1.1' and route[0]['dev'] == 'eth0'
        print(json.dumps({'neigh_before': before, 'route_get': route, 'neigh_after_route_get': after_query}), flush=True)
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
        after = json.loads(command('ip', '-n', a, '-j', '-4', 'neigh', 'show', 'dev', 'eth0', 'nud', 'all'))
        assert len(after) == 1 and after[0]['dst'] == '10.6.1.1'
        assert after[0]['lladdr'] == ROUTER_MAC.hex(':')
        print(json.dumps({'neigh_after_echo': after, 'result': 'isolated cross-subnet UDP echo passed',
                          'scope': 'Linux veth routing and ARP only; no DHCP, physical network or public E2E'}), flush=True)
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
