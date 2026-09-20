#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py inside an owned Linux VM
"""Synchronized isolated TCP close/half-close/reset with kernel state snapshots."""
import argparse
import errno
import json
import os
import platform
import select
import socket
import struct
import subprocess
import sys
import time
import uuid
from enum import StrEnum
from pathlib import Path
from typing import assert_never


class Action(StrEnum):
    SEND = 'send'
    RECV = 'recv'
    EOF = 'eof'
    SHUTDOWN = 'shutdown'
    RESET_RECV = 'reset-recv'
    RESET = 'reset'
    CLOSE = 'close'


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout


def endpoint(server: bool) -> None:
    if server:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.settimeout(5)
            listener.bind(('10.16.0.2', 46016))
            listener.listen(1)
            print('LISTEN', flush=True)
            connection, _ = listener.accept()
    else:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.settimeout(5)
        connection.connect(('10.16.0.2', 46016))
    with connection:
        connection.settimeout(5)
        print('CONNECTED', flush=True)
        for _ in range(20):
            if not select.select([sys.stdin], [], [], 5)[0]:
                raise TimeoutError('endpoint command barrier timed out')
            action = Action(sys.stdin.readline().strip())
            match action:
                case Action.SEND:
                    payload = b'response' if server else b'request'
                    connection.sendall(payload)
                    print(json.dumps({'action': action, 'hex': payload.hex()}), flush=True)
                case Action.RECV:
                    expected = b'request' if server else b'response'
                    data = b''
                    while len(data) < len(expected):
                        part = connection.recv(len(expected) - len(data))
                        assert part, 'unexpected EOF'
                        data += part
                    assert data == expected
                    print(json.dumps({'action': action, 'hex': data.hex()}), flush=True)
                case Action.EOF:
                    data = connection.recv(64)
                    assert data == b''
                    print(json.dumps({'action': action, 'received_hex': data.hex()}), flush=True)
                case Action.SHUTDOWN:
                    connection.shutdown(socket.SHUT_WR)
                    print(json.dumps({'action': action, 'how': 'SHUT_WR'}), flush=True)
                case Action.RESET_RECV:
                    try:
                        data = connection.recv(64)
                    except ConnectionResetError as error:
                        assert error.errno == errno.ECONNRESET
                        print(json.dumps({'action': action, 'errno': error.errno, 'exception': type(error).__name__}), flush=True)
                    else:
                        raise AssertionError(f'expected reset, received {data!r}')
                case Action.RESET:
                    connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                    break
                case Action.CLOSE:
                    break
                case _:
                    assert_never(action)
        else:
            raise AssertionError('endpoint command bound exceeded')
    print(json.dumps({'action': action, 'socket_closed': True}), flush=True)


def capture() -> None:
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as packets:
        packets.bind(('eth0', 0))
        print('READY', flush=True)
        frames: list[str] = []
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            ready = select.select([packets, sys.stdin], [], [], max(0, deadline - time.monotonic()))[0]
            if packets in ready:
                frames.append(packets.recv(65535).hex())
                assert len(frames) <= 256
            if sys.stdin in ready:
                assert sys.stdin.readline().strip() == 'STOP'
                while select.select([packets], [], [], 0)[0]:
                    frames.append(packets.recv(65535).hex())
                print(json.dumps({'interface': 'B/eth0', 'raw_frames': frames}), flush=True)
                return
        raise TimeoutError('capture barrier timed out')


def read(proc: subprocess.Popen[str]) -> str:
    assert proc.stdout is not None
    if not select.select([proc.stdout], [], [], 5)[0]:
        raise TimeoutError('child response barrier timed out')
    return proc.stdout.readline().strip()


def tell(proc: subprocess.Popen[str], action: str) -> str:
    assert proc.stdin is not None
    proc.stdin.write(action + '\n')
    proc.stdin.flush()
    return read(proc)


def states(ns: str) -> list[dict]:
    rows = []
    for line in command('ip', 'netns', 'exec', ns, 'cat', '/proc/net/tcp').splitlines()[1:]:
        fields = line.split()
        if any(int(endpoint.split(':')[1], 16) == 46016 for endpoint in fields[1:3]):
            rows.append({'local_hex': fields[1], 'remote_hex': fields[2], 'state_hex': fields[3]})
    return rows


def scenario(case: str) -> None:
    prefix = 'net16-' + uuid.uuid4().hex[:8]
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
            command('ip', '-n', ns, 'address', 'add', f'10.16.0.{host}/24', 'dev', 'eth0')
            command('ip', '-n', ns, 'link', 'set', 'eth0', 'up')
        for ns, mode in ((b, 'capture'), (b, 'server'), (a, 'client')):
            proc = subprocess.Popen(['ip', 'netns', 'exec', ns, sys.executable, str(Path(__file__).resolve()), mode],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(proc)
            assert read(proc) == {'capture': 'READY', 'server': 'LISTEN', 'client': 'CONNECTED'}[mode]
        watcher, server, client = children
        assert read(server) == 'CONNECTED'
        events = [{'role': 'client', **json.loads(tell(client, 'send'))}, {'role': 'server', **json.loads(tell(server, 'recv'))}]
        snapshots = [{'stage': 'established', 'A': states(a), 'B': states(b)}]
        assert all(len(snapshots[-1][role]) == 1 and snapshots[-1][role][0]['state_hex'] == '01' for role in ('A', 'B'))
        if case == 'reset':
            events.append({'role': 'server', **json.loads(tell(server, 'reset'))})
            events.append({'role': 'client', **json.loads(tell(client, 'reset-recv'))})
            snapshots.append({'stage': 'reset', 'A': states(a), 'B': states(b)})
            assert snapshots[-1]['A'] == [] and snapshots[-1]['B'] == []
            events.append({'role': 'client', **json.loads(tell(client, 'close'))})
        else:
            active, passive = (server, client) if case == 'normal' else (client, server)
            events.append({'role': 'active', **json.loads(tell(active, 'shutdown'))})
            events.append({'role': 'passive', **json.loads(tell(passive, 'eof'))})
            deadline = time.monotonic() + 2
            while True:
                half = {'stage': 'half-closed', 'A': states(a), 'B': states(b)}
                if any(row['state_hex'] == '05' for row in half['B' if case == 'normal' else 'A']):
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('FIN_WAIT2 not observed')
                time.sleep(0.01)
            assert any(row['state_hex'] == '08' for row in half['A' if case == 'normal' else 'B'])
            snapshots.append(half)
            if case == 'half-close':
                events.append({'role': 'server-after-EOF', **json.loads(tell(server, 'send'))})
                events.append({'role': 'client-after-SHUT_WR', **json.loads(tell(client, 'recv'))})
            events.append({'role': 'passive', **json.loads(tell(passive, 'shutdown'))})
            events.append({'role': 'active', **json.loads(tell(active, 'eof'))})
            final = {'stage': 'closed-directions', 'A': states(a), 'B': states(b)}
            assert any(row['state_hex'] == '06' for row in final['B' if case == 'normal' else 'A'])
            snapshots.append(final)
            for role, endpoint_proc in (('client', client), ('server', server)):
                events.append({'role': role, **json.loads(tell(endpoint_proc, 'close'))})
        captured = json.loads(tell(watcher, 'STOP'))
        decoded = []
        for index, raw in enumerate(captured['raw_frames']):
            frame = bytes.fromhex(raw)
            if len(frame) >= 54 and frame[12:14] == b'\x08\x00' and frame[23] == 6:
                offset = 14 + (frame[14] & 15) * 4
                ports = [int.from_bytes(frame[offset:offset + 2]), int.from_bytes(frame[offset + 2:offset + 4])]
                if 46016 in ports:
                    decoded.append({'frame_index': index, 'source': socket.inet_ntoa(frame[26:30]),
                                    'destination': socket.inet_ntoa(frame[30:34]), 'source_port': ports[0],
                                    'destination_port': ports[1], 'flags': frame[offset + 13]})
        assert any(row['flags'] & 4 for row in decoded) if case == 'reset' else sum(bool(row['flags'] & 1) for row in decoded) >= 2
        print(json.dumps({'case': case, 'prefix': prefix, 'events': events, 'states': snapshots,
                          'capture': captured, 'decoded': decoded}), flush=True)
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
    match args.mode:
        case 'client': endpoint(False)
        case 'server': endpoint(True)
        case 'capture': capture()
        case 'lab':
            if platform.system() != 'Linux' or os.geteuid() != 0:
                raise SystemExit('Requires root in owned Linux VM')
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(), 'state_source': '/proc/net/tcp'}), flush=True)
            for case in ('normal', 'half-close', 'reset'):
                scenario(case)
        case _: assert_never(args.mode)


if __name__ == '__main__':
    main()
