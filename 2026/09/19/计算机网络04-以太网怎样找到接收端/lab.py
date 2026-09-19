#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Linux-only, isolated four-port bridge; no physical or default-route changes."""
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
from pathlib import Path
from typing import assert_never

ETHERTYPE = b'\x88\xb5'
MACS = {name: bytes.fromhex(f'0200000004{index:02x}')
        for index, name in enumerate('abcd', 1)}


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout


def observe(token: str) -> None:
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as capture:
        capture.bind(('eth0', 0))
        print('READY', flush=True)
        if sys.stdin.readline().strip() != 'GO':
            raise EOFError('missing observer start barrier')
        frames: list[str] = []
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if not select.select([capture], [], [], max(0, deadline - time.monotonic()))[0]:
                break
            frame = capture.recv(65535)
            if frame[12:14] == ETHERTYPE and frame[14:].startswith(token.encode()):
                frames.append(frame.hex())
        print(json.dumps(frames), flush=True)


def send(source: str, destination: str, token: str) -> None:
    target = b'\xff' * 6 if destination == 'broadcast' else MACS[destination]
    frame = target + MACS[source] + ETHERTYPE + token.encode().ljust(46, b'\x00')
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW) as sender:
        sender.bind(('eth0', 0))
        sent = sender.send(frame)
        assert sent == len(frame)


def lab() -> None:
    if platform.system() != 'Linux' or os.geteuid() != 0:
        raise SystemExit('Requires root in an owned Linux VM; no host network changes permitted')
    prefix = 'net04-' + uuid.uuid4().hex[:8]
    center = prefix + '-s'
    namespaces = [center] + [prefix + '-' + name for name in 'abcd']
    owned: list[str] = []
    script = str(Path(__file__).resolve())
    children: list[subprocess.Popen[str]] = []
    try:
        for ns in namespaces:
            command('ip', 'netns', 'add', ns)
            owned.append(ns)
        command('ip', '-n', center, 'link', 'add', 'br0', 'type', 'bridge',
                'vlan_filtering', '1', 'vlan_default_pvid', '0', 'stp_state', '0')
        command('ip', '-n', center, 'link', 'set', 'br0', 'up')
        for name in 'abcd':
            endpoint = prefix + '-' + name
            command('ip', '-n', center, 'link', 'add', 'p' + name, 'type', 'veth', 'peer', 'name', 'e' + name)
            command('ip', '-n', center, 'link', 'set', 'e' + name, 'netns', endpoint)
            command('ip', '-n', endpoint, 'link', 'set', 'e' + name, 'name', 'eth0')
            command('ip', '-n', endpoint, 'link', 'set', 'eth0', 'promisc', 'on', 'up')
            command('ip', '-n', center, 'link', 'set', 'p' + name, 'master', 'br0')
            command('ip', '-n', center, 'link', 'set', 'p' + name, 'up')
            command('ip', 'netns', 'exec', center, 'bridge', 'vlan', 'add', 'dev', 'p' + name,
                    'vid', '20' if name == 'd' else '10', 'pvid', 'untagged')
        print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                          'ip': command('ip', '-V').strip(), 'prefix': prefix}), flush=True)
        print(json.dumps({'vlan': json.loads(command('ip', 'netns', 'exec', center, 'bridge', '-j', 'vlan', 'show'))}), flush=True)
        cases = [('unknown', 'a', 'b', {'b': 1, 'c': 1, 'd': 0}),
                 ('learn_b', 'b', 'a', {'a': 1, 'c': 0, 'd': 0}),
                 ('known', 'a', 'b', {'b': 1, 'c': 0, 'd': 0}),
                 ('broadcast', 'a', 'broadcast', {'b': 1, 'c': 1, 'd': 0}),
                 ('vlan20', 'd', 'a', {'a': 0, 'b': 0, 'c': 0})]
        for label, source, destination, expected in cases:
            before = json.loads(command('ip', 'netns', 'exec', center, 'bridge', '-j', 'fdb', 'show', 'br', 'br0'))
            if label == 'unknown':
                assert not any(row['mac'] == '02:00:00:00:04:02' for row in before)
            if label == 'known':
                assert any(row['mac'] == '02:00:00:00:04:02' and row.get('vlan') == 10 and row.get('ifname') == 'pb' for row in before)
            token = prefix + ':' + label
            watchers: dict[str, subprocess.Popen[str]] = {}
            for endpoint in expected:
                proc = subprocess.Popen(['ip', 'netns', 'exec', prefix + '-' + endpoint,
                                         sys.executable, script, 'observe', '--token', token],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                children.append(proc)
                watchers[endpoint] = proc
                assert proc.stdout is not None
                if not select.select([proc.stdout], [], [], 5)[0] or proc.stdout.readline().strip() != 'READY':
                    raise TimeoutError('capture did not become ready')
            for proc in watchers.values():
                assert proc.stdin is not None
                proc.stdin.write('GO\n')
                proc.stdin.flush()
            command('ip', 'netns', 'exec', prefix + '-' + source, sys.executable, script,
                    'send', '--source', source, '--destination', destination, '--token', token)
            observed: dict[str, int] = {}
            raw: dict[str, list[str]] = {}
            for endpoint, proc in watchers.items():
                stdout, stderr = proc.communicate(timeout=5)
                if proc.returncode != 0:
                    raise subprocess.CalledProcessError(proc.returncode, proc.args, stderr=stderr)
                raw[endpoint] = json.loads(stdout)
                observed[endpoint] = len(raw[endpoint])
            fdb = json.loads(command('ip', 'netns', 'exec', center, 'bridge', '-j', 'fdb', 'show', 'br', 'br0'))
            print(json.dumps({'case': label, 'expected': expected, 'observed': observed,
                              'raw_frames': raw, 'fdb_before': before, 'fdb': fdb}), flush=True)
            assert observed == expected, label
        print(json.dumps({'result': 'five isolated bridge cases passed',
                          'scope': 'Linux veth + AF_PACKET, not physical Ethernet or STP convergence'}), flush=True)
    finally:
        for proc in children:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
        for ns in reversed(owned):
            command('ip', 'netns', 'delete', ns)
        remaining = command('ip', 'netns', 'list')
        assert not any(ns in remaining for ns in owned)
        print(json.dumps({'cleanup': 'only namespaces created by this run deleted', 'owned': owned}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['lab', 'observe', 'send'], nargs='?', default='lab')
    parser.add_argument('--token', default='manual')
    parser.add_argument('--source', choices=list(MACS), default='a')
    parser.add_argument('--destination', choices=list(MACS) + ['broadcast'], default='b')
    args = parser.parse_args()
    match args.mode:
        case 'observe':
            observe(args.token)
        case 'send':
            send(args.source, args.destination, args.token)
        case 'lab':
            lab()
        case _:
            assert_never(args.mode)


if __name__ == '__main__':
    main()
