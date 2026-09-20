#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py in a dedicated Linux VM
"""Observe a real zero-window event before resuming the paused TCP receiver."""
import argparse
import hashlib
import json
import os
import platform
import select
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import assert_never


@dataclass(frozen=True, slots=True)
class Segment:
    source: str
    destination: str
    source_port: int
    destination_port: int
    seq: int
    ack: int
    flags: int
    window: int
    payload_length: int
    window_scale: int | None


def decode(frame: bytes) -> Segment | None:
    if len(frame) < 54 or frame[12:14] != b'\x08\x00' or frame[23] != 6:
        return None
    ihl = (frame[14] & 15) * 4
    offset = 14 + ihl
    end = 14 + int.from_bytes(frame[16:18])
    assert ihl >= 20 and offset + 20 <= end <= len(frame)
    thl = (frame[offset + 12] >> 4) * 4
    assert thl >= 20 and offset + thl <= end
    sport, dport = int.from_bytes(frame[offset:offset + 2]), int.from_bytes(frame[offset + 2:offset + 4])
    if 46018 not in (sport, dport):
        return None
    scale = None
    cursor = offset + 20
    while cursor < offset + thl:
        kind = frame[cursor]
        if kind == 0:
            break
        if kind == 1:
            cursor += 1
            continue
        assert cursor + 2 <= offset + thl
        size = frame[cursor + 1]
        assert size >= 2 and cursor + size <= offset + thl
        if kind == 3:
            assert size == 3
            scale = frame[cursor + 2]
        cursor += size
    return Segment(socket.inet_ntoa(frame[26:30]), socket.inet_ntoa(frame[30:34]), sport, dport,
                   int.from_bytes(frame[offset + 4:offset + 8]), int.from_bytes(frame[offset + 8:offset + 12]),
                   frame[offset + 13], int.from_bytes(frame[offset + 14:offset + 16]), end - offset - thl, scale)


def command(*args: str) -> str:
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, text=True, timeout=10).stdout


def read(proc: subprocess.Popen[str]) -> str:
    assert proc.stdout is not None
    if not select.select([proc.stdout], [], [], 12)[0]:
        raise TimeoutError('child barrier')
    data = bytearray()
    while True:
        byte = os.read(proc.stdout.fileno(), 1)
        if byte in (b'\n', b''):
            return data.decode().strip()
        data.extend(byte)


def signal(proc: subprocess.Popen[str], action: str) -> None:
    assert proc.stdin is not None
    proc.stdin.write(action + '\n')
    proc.stdin.flush()


def barrier() -> None:
    if not select.select([sys.stdin], [], [], 12)[0]:
        raise TimeoutError('endpoint barrier')
    assert sys.stdin.readline().strip() == 'GO'


def endpoint(server: bool) -> None:
    payload = bytes(range(256)) * 1024
    if server:
        with socket.socket() as listener:
            listener.settimeout(12)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            print(json.dumps({'rcvbuf_requested': 4096, 'listener_actual': listener.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)}), flush=True)
            listener.bind(('10.18.0.2', 46018))
            listener.listen(1)
            print('LISTEN', flush=True)
            connection, _ = listener.accept()
    else:
        connection = socket.socket()
        connection.settimeout(12)
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
        connection.connect(('10.18.0.2', 46018))
    with connection:
        connection.settimeout(12)
        print(json.dumps({'connected': True, 'rcvbuf': connection.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
                          'sndbuf': connection.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)}), flush=True)
        barrier()
        if server:
            actual = bytearray()
            while len(actual) < len(payload):
                chunk = connection.recv(min(65536, len(payload) - len(actual)))
                assert chunk
                actual.extend(chunk)
            assert actual == payload
            print(json.dumps({'event': 'received', 'bytes': len(actual), 'sha256': hashlib.sha256(actual).hexdigest(),
                              'time_ns': time.monotonic_ns()}), flush=True)
        else:
            print(json.dumps({'event': 'enter_sendall', 'time_ns': time.monotonic_ns(), 'bytes': len(payload)}), flush=True)
            connection.sendall(payload)
            print(json.dumps({'event': 'sendall_return', 'time_ns': time.monotonic_ns()}), flush=True)
        barrier()
        connection.shutdown(socket.SHUT_WR)
        assert connection.recv(1) == b''
    print('CLOSED', flush=True)


def capture() -> None:
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as packets:
        packets.bind(('eth0', 0))
        print('READY', flush=True)
        frames = []
        announced = False
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            ready = select.select([packets, sys.stdin], [], [], max(0, deadline - time.monotonic()))[0]
            if packets in ready:
                frame = packets.recv(65535)
                row = {'time_ns': time.monotonic_ns(), 'hex': frame.hex()}
                segment = decode(frame)
                if segment is not None:
                    row['decoded'] = asdict(segment)
                frames.append(row)
                assert len(frames) <= 4096
                if segment is not None and segment.source_port == 46018 and segment.window == 0 and not announced:
                    print(json.dumps({'event': 'zero_window', 'frame_index': len(frames) - 1, 'time_ns': row['time_ns']}), flush=True)
                    announced = True
            if sys.stdin in ready:
                assert sys.stdin.readline().strip() == 'STOP'
                print(json.dumps(frames), flush=True)
                return
        raise TimeoutError('capture deadline')


def lab() -> None:
    prefix = 'net18-' + uuid.uuid4().hex[:8]
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
        setup = {}
        for ns, host in ((a, 1), (b, 2)):
            command('ip', '-n', ns, 'address', 'add', f'10.18.0.{host}/24', 'dev', 'eth0')
            command('ip', '-n', ns, 'link', 'set', 'eth0', 'up')
        for ns, mode in ((b, 'capture'), (b, 'server'), (a, 'client')):
            proc = subprocess.Popen(['ip', 'netns', 'exec', ns, sys.executable, str(Path(__file__).resolve()), mode],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            children.append(proc)
            if mode == 'server':
                setup['listener'] = json.loads(read(proc))
            line = read(proc)
            if mode == 'client':
                setup['client'] = json.loads(line)
            else:
                assert line == ('READY' if mode == 'capture' else 'LISTEN')
        watcher, server, client = children
        setup['server'] = json.loads(read(server))
        signal(client, 'GO')
        entered = json.loads(read(client))
        assert entered['event'] == 'enter_sendall'
        zero = json.loads(read(watcher))
        assert zero['event'] == 'zero_window'
        assert client.stdout is not None
        assert not select.select([client.stdout], [], [], 0)[0], 'sendall already returned'
        snapshots = {role: command('ip', 'netns', 'exec', ns, 'ss', '-tinm', 'sport = :46018 or dport = :46018') for role, ns in (('A', a), ('B', b))}
        assert not select.select([client.stdout], [], [], 0)[0], 'sendall returned before resume'
        resumed = time.monotonic_ns()
        signal(server, 'GO')
        sent = json.loads(read(client))
        received = json.loads(read(server))
        assert sent['event'] == 'sendall_return' and received['event'] == 'received'
        for proc in (client, server):
            signal(proc, 'GO')
        client_closed, server_closed = read(client), read(server)
        assert client_closed == server_closed == 'CLOSED'
        signal(watcher, 'STOP')
        frames = json.loads(read(watcher))
        syns = [r['decoded'] for r in frames if 'decoded' in r and r['decoded']['flags'] & 2]
        assert len(syns) == 2 and all(r['window_scale'] is not None for r in syns)
        assert any('decoded' in r and r['decoded']['source_port'] == 46018 and r['decoded']['window'] > 0 for r in frames[zero['frame_index'] + 1:])
        print(json.dumps({'prefix': prefix, 'setup': setup, 'entered': entered, 'zero': zero,
                          'sendall_return_absent_before_resume': True, 'paused_ss': snapshots, 'resume_ns': resumed,
                          'sent': sent, 'received': received, 'handshake': syns, 'capture': frames}), flush=True)
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
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(), 'ss': command('ss', '-V')}), flush=True)
            lab()
        case _: assert_never(args.mode)


if __name__ == '__main__':
    main()
