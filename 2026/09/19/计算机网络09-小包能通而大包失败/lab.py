#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py (owned Linux VM only)
"""Fresh isolated namespaces per UDP/MTU case; IPv4 DF and IPv6 PMTUD."""
import argparse
import errno
import json
import os
import platform
import re
import select
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import assert_never


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout


def endpoint(version: int, size: int, server: bool) -> None:
    family = socket.AF_INET6 if version == 6 else socket.AF_INET
    address = '2001:db8:9:2::2' if version == 6 else '10.9.2.2'
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as capture:
        capture.bind(('eth0', 0))
        with socket.socket(family, socket.SOCK_DGRAM) as udp:
            udp.settimeout(1)
            result: dict[str, str | int | None] = {'outcome': 'not-started'}
            phase = 'bind' if server else 'setsockopt'
            sent_bytes = 0
            try:
                if server:
                    udp.bind((address, 46009))
                    print('READY', flush=True)
                    phase = 'recv'
                    data, peer = udp.recvfrom(65535)
                    count = udp.sendto(b'ACK', peer)
                    sent_bytes = count
                    assert count == 3
                    result = {'outcome': 'received', 'bytes': len(data)}
                else:
                    level, option = (socket.IPPROTO_IPV6, 23) if version == 6 else (socket.IPPROTO_IP, 10)
                    udp.setsockopt(level, option, 2)
                    phase = 'connect'
                    udp.connect((address, 46009))
                    phase = 'send'
                    count = udp.send(b'x' * size)
                    sent_bytes = count
                    phase = 'recv'
                    assert count == size
                    data = udp.recv(100)
                    assert data == b'ACK'
                    result = {'outcome': 'ack', 'bytes': count}
            except TimeoutError:
                result = {'outcome': 'timeout'}
            except OSError as error:
                result = {'outcome': 'os-error', 'errno': error.errno, 'message': error.strerror}
            result.update({'phase': phase, 'sent_bytes': sent_bytes})
        frames: list[str] = []
        while select.select([capture], [], [], 0)[0]:
            frames.append(capture.recv(65535).hex())
    print(json.dumps({'application': result, 'frames': frames}), flush=True)


def scenario(version: int, size: int, condition: str) -> None:
    prefix = 'net09-' + uuid.uuid4().hex[:8]
    a, r, b = [prefix + '-' + suffix for suffix in 'arb']
    owned: list[str] = []
    children: list[subprocess.Popen[str]] = []
    try:
        for namespace in (a, r, b):
            command('ip', 'netns', 'add', namespace)
            owned.append(namespace)
            command('ip', '-n', namespace, 'link', 'set', 'lo', 'up')
        for namespace, side, subnet, mtu in ((a, 'left', 1, 1500), (b, 'right', 2, 1280)):
            command('ip', '-n', r, 'link', 'add', side, 'type', 'veth', 'peer', 'name', 'ep')
            command('ip', '-n', r, 'link', 'set', 'ep', 'netns', namespace)
            command('ip', '-n', namespace, 'link', 'set', 'ep', 'name', 'eth0')
            for ns, dev, host in ((r, side, 1), (namespace, 'eth0', 2)):
                command('ip', '-n', ns, 'link', 'set', dev, 'mtu', str(mtu))
                command('ip', '-n', ns, 'address', 'add', f'10.9.{subnet}.{host}/24', 'dev', dev)
                command('ip', '-n', ns, '-6', 'address', 'add', f'2001:db8:9:{subnet}::{host}/64', 'dev', dev)
                command('ip', '-n', ns, 'link', 'set', dev, 'up')
            command('ip', '-n', namespace, 'route', 'add', 'default', 'via', f'10.9.{subnet}.1')
            command('ip', '-n', namespace, '-6', 'route', 'add', 'default', 'via', f'2001:db8:9:{subnet}::1')
        command('ip', 'netns', 'exec', r, 'sysctl', '-w', 'net.ipv4.ip_forward=1', 'net.ipv6.conf.all.forwarding=1')
        deadline = time.monotonic() + 10
        while True:
            rows = [address for ns in owned
                    for interface in json.loads(command('ip', '-n', ns, '-j', '-6', 'address', 'show'))
                    for address in interface['addr_info']]
            assert not any(row.get('dadfailed', False) for row in rows)
            if not any(row.get('tentative', False) for row in rows):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('DAD did not complete')
            time.sleep(0.05)
        if condition == 'no-route':
            command('ip', '-n', a, f'-{version}', 'route', 'del', 'default')
        if condition == 'blackhole':
            command('ip', 'netns', 'exec', r, 'nft', 'add', 'table', 'inet', 'net09')
            command('ip', 'netns', 'exec', r, 'nft', 'add', 'chain', 'inet', 'net09', 'out',
                    '{ type filter hook output priority 0; policy accept; }')
            selector = ['icmpv6', 'type', '2'] if version == 6 else ['icmp', 'type', '3', 'icmp', 'code', '4']
            command('ip', 'netns', 'exec', r, 'nft', 'add', 'rule', 'inet', 'net09', 'out', *selector, 'counter', 'drop')
        links = json.loads(command('ip', '-n', r, '-j', 'link', 'show'))
        assert {row['ifname']: row['mtu'] for row in links if row['ifname'] != 'lo'} == {'left': 1500, 'right': 1280}
        script = str(Path(__file__).resolve())
        proc = subprocess.Popen(['ip', 'netns', 'exec', b, sys.executable, script, 'server', '--version', str(version)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        children.append(proc)
        assert proc.stdout is not None
        if not select.select([proc.stdout], [], [], 5)[0] or proc.stdout.readline().strip() != 'READY':
            raise TimeoutError('server capture not ready')
        client = json.loads(command('ip', 'netns', 'exec', a, sys.executable, script, 'client',
                                    '--version', str(version), '--size', str(size)))
        stdout, stderr = proc.communicate(timeout=5)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, proc.args, stderr=stderr)
        receiver = json.loads(stdout)
        summaries: dict[str, list[dict[str, str | int]]] = {'A': [], 'B': []}
        for name, evidence in (('A', client), ('B', receiver)):
            for raw in evidence['frames']:
                frame = bytes.fromhex(raw)
                if len(frame) >= 34 and frame[12:14] == b'\x08\x00':
                    header = (frame[14] & 15) * 4
                    offset = 14 + header
                    row: dict[str, str | int] = {'version': 4, 'length': int.from_bytes(frame[16:18]),
                          'destination': socket.inet_ntoa(frame[30:34]), 'protocol': frame[23],
                          'df': int(bool(int.from_bytes(frame[20:22]) & 0x4000))}
                    if frame[23] == 1 and len(frame) >= offset + 8:
                        row.update({'type': frame[offset], 'code': frame[offset + 1],
                                    'mtu': int.from_bytes(frame[offset + 6:offset + 8])})
                    summaries[name].append(row)
                if len(frame) >= 54 and frame[12:14] == b'\x86\xdd':
                    row = {'version': 6, 'length': 40 + int.from_bytes(frame[18:20]),
                           'destination': socket.inet_ntop(socket.AF_INET6, frame[38:54]), 'protocol': frame[20]}
                    if frame[20] == 58 and len(frame) >= 62:
                        row.update({'type': frame[54], 'code': frame[55], 'mtu': int.from_bytes(frame[58:62])})
                    summaries[name].append(row)
        errors = [row for row in summaries['A'] if row['version'] == version
                  and row.get('type') == (2 if version == 6 else 3) and row.get('code') == (0 if version == 6 else 4)]
        filter_stats = command('ip', 'netns', 'exec', r, 'nft', 'list', 'table', 'inet', 'net09') if condition == 'blackhole' else None
        print(json.dumps({'case': [version, size, condition], 'prefix': prefix,
                          'A': client, 'B': receiver, 'decoded': summaries, 'filter': filter_stats, 'router_links': links}), flush=True)
        small = size <= (1232 if version == 6 else 1252)
        destination = '2001:db8:9:2::2' if version == 6 else '10.9.2.2'
        packets = {name: [row for row in rows if row['version'] == version
                         and row['protocol'] == 17 and row['destination'] == destination]
                   for name, rows in summaries.items()}
        if condition == 'no-route':
            assert not packets['A'] and not packets['B']
        else:
            assert len(packets['A']) == 1 and packets['A'][0]['length'] == size + (48 if version == 6 else 28)
            if version == 4:
                assert packets['A'][0]['df'] == 1
            assert len(packets['B']) == (1 if small else 0)
            assert client['application']['sent_bytes'] == size and client['application']['phase'] == 'recv'
        if condition == 'no-route':
            assert client['application']['outcome'] == 'os-error' and client['application']['errno'] == errno.ENETUNREACH
        elif small:
            assert client['application']['outcome'] == 'ack' and receiver['application']['bytes'] == size
        elif condition == 'blackhole':
            assert client['application']['outcome'] == 'timeout' and not errors
            assert filter_stats is not None and re.search(r'counter packets [1-9]', filter_stats)
        else:
            assert client['application']['outcome'] == 'os-error' and client['application']['errno'] == errno.EMSGSIZE
            assert errors and all(row['mtu'] == 1280 for row in errors)
        if not small or condition == 'no-route':
            assert receiver['application']['outcome'] == 'timeout'
        print(json.dumps({'passed': [version, size, condition]}), flush=True)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
        for ns in reversed(owned):
            command('ip', 'netns', 'delete', ns)
        remaining = command('ip', 'netns', 'list')
        assert not any(ns in remaining for ns in owned)
        print(json.dumps({'cleanup': owned}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=['lab', 'client', 'server'], default='lab')
    parser.add_argument('--version', type=int, choices=[4, 6], default=4)
    parser.add_argument('--size', type=int, choices=range(1, 1401), default=1252)
    args = parser.parse_args()
    match args.mode:
        case 'client':
            endpoint(args.version, args.size, False)
        case 'server':
            endpoint(args.version, args.size, True)
        case 'lab':
            if platform.system() != 'Linux' or os.geteuid() != 0:
                raise SystemExit('Requires root in owned Linux VM')
            constants = {'IP_MTU_DISCOVER': 10, 'IP_PMTUDISC_DO': 2, 'IPV6_MTU_DISCOVER': 23, 'IPV6_PMTUDISC_DO': 2}
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                              'ip': command('ip', '-V').strip(), 'constants_checked_against_linux_v6_18_uapi': constants,
                              'nft': shutil.which('nft'), 'scope': 'isolated veth only; no production traffic'}), flush=True)
            for version, threshold in ((4, 1252), (6, 1232)):
                scenario(version, threshold, 'normal')
                scenario(version, threshold + 1, 'normal')
                scenario(version, 100, 'no-route')
                if shutil.which('nft'):
                    scenario(version, threshold + 1, 'blackhole')
                else:
                    print(json.dumps({'skipped': [version, 'blackhole'], 'reason': 'nft unavailable; no dependencies installed'}), flush=True)
        case _:
            assert_never(args.mode)


if __name__ == '__main__':
    main()
