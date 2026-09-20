#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py in a dedicated Linux VM
"""Bounded isolated TCP delay versus first-data drop; no recovery-algorithm attribution."""
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


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout


def read(proc: subprocess.Popen[str]) -> str:
    assert proc.stdout is not None
    if not select.select([proc.stdout], [], [], 8)[0]:
        raise TimeoutError('child barrier')
    return proc.stdout.readline().strip()


def tell(proc: subprocess.Popen[str], text: str) -> str:
    assert proc.stdin is not None
    proc.stdin.write(text + '\n')
    proc.stdin.flush()
    return read(proc)


def barrier() -> None:
    if not select.select([sys.stdin], [], [], 8)[0]:
        raise TimeoutError('endpoint barrier')
    assert sys.stdin.readline().strip() == 'GO'


def endpoint(server: bool) -> None:
    payload = b'0123456789abcdef0123456789abcdef'
    if server:
        with socket.socket() as listener:
            listener.settimeout(8)
            listener.bind(('10.17.0.2', 46017))
            listener.listen(1)
            print('LISTEN', flush=True)
            connection, _ = listener.accept()
    else:
        connection = socket.socket()
        connection.settimeout(8)
        connection.connect(('10.17.0.2', 46017))
    with connection:
        connection.settimeout(8)
        print('CONNECTED', flush=True)
        barrier()
        start = time.monotonic_ns()
        if not server:
            connection.sendall(payload)
        actual = b''
        while len(actual) < len(payload):
            part = connection.recv(len(payload) - len(actual))
            assert part
            actual += part
        assert actual == payload
        if server:
            connection.sendall(actual)
        print(json.dumps({'role': 'B' if server else 'A', 'start_ns': start,
                          'complete_ns': time.monotonic_ns(), 'received_hex': actual.hex()}), flush=True)
        barrier()
        connection.shutdown(socket.SHUT_WR)
        assert connection.recv(1) == b''
    print('CLOSED', flush=True)


def capture() -> None:
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as packets:
        packets.bind(('eth0', 0))
        print('READY', flush=True)
        frames = []
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            ready = select.select([packets, sys.stdin], [], [], max(0, deadline - time.monotonic()))[0]
            if packets in ready:
                frame = packets.recv(65535)
                frames.append({'time_ns': time.monotonic_ns(), 'hex': frame.hex()})
                assert len(frames) <= 256
            if sys.stdin in ready:
                assert sys.stdin.readline().strip() == 'STOP'
                print(json.dumps(frames), flush=True)
                return
        raise TimeoutError('capture deadline')


def scenario(delay: bool) -> None:
    prefix = 'net17-' + uuid.uuid4().hex[:8]
    a, b = prefix + '-a', prefix + '-b'
    owned: list[str] = []
    children: list[subprocess.Popen[str]] = []
    try:
        for ns in (a, b):
            command('ip', 'netns', 'add', ns)
            owned.append(ns)
        command('ip', '-n', a, 'link', 'add', 'eth0', 'type', 'veth', 'peer', 'name', 'peer0')
        command('ip', '-n', a, 'link', 'set', 'peer0', 'netns', b)
        command('ip', '-n', b, 'link', 'set', 'peer0', 'name', 'eth0')
        for ns, host in ((a, 1), (b, 2)):
            command('ip', '-n', ns, 'address', 'add', f'10.17.0.{host}/24', 'dev', 'eth0')
            command('ip', '-n', ns, 'link', 'set', 'eth0', 'up')
        for ns, mode in ((a, 'capture'), (b, 'capture'), (b, 'server'), (a, 'client')):
            proc = subprocess.Popen(['ip', 'netns', 'exec', ns, sys.executable, str(Path(__file__).resolve()), mode],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(proc)
            assert read(proc) == {'capture': 'READY', 'server': 'LISTEN', 'client': 'CONNECTED'}[mode]
        watch_a, watch_b, server, client = children
        assert read(server) == 'CONNECTED'
        if delay:
            rule = 'tc qdisc add dev eth0 root netem limit 100 delay 80ms'
            command('ip', 'netns', 'exec', a, *rule.split())
            inspection = ['ip', 'netns', 'exec', a, 'tc', '-s', 'qdisc', 'show', 'dev', 'eth0']
        else:
            rule = ('table ip experiment { chain incoming { type filter hook input priority 0; policy accept; '
                    'ip saddr 10.17.0.1 tcp dport 46017 ip length > 60 '
                    'tcp flags & (syn | fin | rst) == 0 numgen inc mod 100 == 0 counter drop; }\n}')
            subprocess.run(['ip', 'netns', 'exec', b, 'nft', '-f', '-'], input=rule + '\n', text=True,
                           stdout=subprocess.PIPE, check=True, timeout=10)
            inspection = ['ip', 'netns', 'exec', b, 'nft', 'list', 'table', 'ip', 'experiment']
        before = command(*inspection)
        injected_ns = time.monotonic_ns()
        assert server.stdin is not None
        server.stdin.write('GO\n')
        server.stdin.flush()
        client_result = json.loads(tell(client, 'GO'))
        server_result = json.loads(read(server))
        after = command(*inspection)
        if not delay:
            assert 'counter packets 1 bytes 84' in after
        for proc in (client, server):
            assert proc.stdin is not None
            proc.stdin.write('GO\n')
            proc.stdin.flush()
        assert read(client) == 'CLOSED'
        assert read(server) == 'CLOSED'
        captures = {'A': json.loads(tell(watch_a, 'STOP')), 'B': json.loads(tell(watch_b, 'STOP'))}
        decoded = []
        for role, frames in captures.items():
            for index, raw in enumerate(frames):
                frame = bytes.fromhex(raw['hex'])
                if len(frame) < 54 or frame[12:14] != b'\x08\x00' or frame[23] != 6:
                    continue
                ihl = (frame[14] & 15) * 4
                end = 14 + int.from_bytes(frame[16:18])
                offset = 14 + ihl
                assert ihl >= 20 and offset + 20 <= end <= len(frame)
                thl = (frame[offset + 12] >> 4) * 4
                assert thl >= 20 and offset + thl <= end
                sport, dport = int.from_bytes(frame[offset:offset + 2]), int.from_bytes(frame[offset + 2:offset + 4])
                if 46017 not in (sport, dport):
                    continue
                decoded.append({'capture': role, 'frame_index': index, 'time_ns': raw['time_ns'],
                                'source': socket.inet_ntoa(frame[26:30]), 'destination': socket.inet_ntoa(frame[30:34]),
                                'source_port': sport, 'destination_port': dport,
                                'seq': int.from_bytes(frame[offset + 4:offset + 8]),
                                'ack': int.from_bytes(frame[offset + 8:offset + 12]), 'flags': frame[offset + 13],
                                'payload_hex': frame[offset + thl:end].hex()})
        observed = {}
        for role in ('A', 'B'):
            data = [row for row in decoded if row['capture'] == role and row['source'] == '10.17.0.1' and row['payload_hex']]
            assert data and all(row['payload_hex'] == client_result['received_hex'] for row in data)
            assert len({row['seq'] for row in data}) == 1
            observed[role] = {'count': len(data), 'seq': data[0]['seq'],
                              'gaps_ms': [(right['time_ns'] - left['time_ns']) / 1e6 for left, right in zip(data, data[1:])]}
            assert len(data) == 1 if delay else len(data) >= 2
        print(json.dumps({'case': 'delay' if delay else 'drop', 'prefix': prefix, 'rule': rule,
                          'before': before, 'after': after, 'injected_ns': injected_ns,
                          'application': [client_result, server_result], 'captures': captures,
                          'decoded': decoded, 'same_payload_observations': observed}), flush=True)
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
        assert not any(ns in command('ip', 'netns', 'list') for ns in owned)
        print(json.dumps({'cleanup': owned}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['lab', 'client', 'server', 'capture'], nargs='?', default='lab')
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        raise SystemExit('Requires root in owned Linux VM')
    match args.mode:
        case 'client': endpoint(False)
        case 'server': endpoint(True)
        case 'capture': capture()
        case 'lab':
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                              'tc': command('tc', '-V'), 'nft': command('nft', '--version')}), flush=True)
            scenario(True)
            scenario(False)
        case _: assert_never(args.mode)


if __name__ == '__main__':
    main()
