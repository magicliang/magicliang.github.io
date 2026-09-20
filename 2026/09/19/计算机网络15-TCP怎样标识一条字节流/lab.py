#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py (owned Linux VM only)
"""Real isolated TCP with raw B/eth0 capture and optional netem reordering."""
import argparse
import json
import os
import platform
import select
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Final, assert_never

PAYLOAD: Final = b''.join(f'{number:07d};'.encode() for number in range(8))


def command(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=20).stdout


def client() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        connection.connect(('10.15.0.2', 46015))
        for offset in range(0, len(PAYLOAD), 8):
            connection.sendall(PAYLOAD[offset:offset + 8])
        connection.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        for _ in range(100):
            part = connection.recv(7)
            if not part:
                break
            chunks.append(part)
        else:
            raise AssertionError('client read bound exceeded')
        assert b''.join(chunks) == PAYLOAD
        print(json.dumps({'echo_hex': b''.join(chunks).hex(), 'local': connection.getsockname()}))


def server() -> None:
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as capture, socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        capture.bind(('eth0', 0))
        listener.settimeout(5)
        listener.bind(('10.15.0.2', 46015))
        listener.listen(1)
        print('READY', flush=True)
        connection, peer = listener.accept()
        with connection:
            connection.settimeout(5)
            chunks: list[bytes] = []
            for _ in range(100):
                part = connection.recv(3)
                if not part:
                    break
                chunks.append(part)
            else:
                raise AssertionError('server read bound exceeded')
            received = b''.join(chunks)
            assert received == PAYLOAD and peer[0] == '10.15.0.1'
            connection.sendall(received)
            connection.shutdown(socket.SHUT_WR)
        frames: list[str] = []
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if not select.select([capture], [], [], max(0, deadline - time.monotonic()))[0]:
                break
            frames.append(capture.recv(65535).hex())
            assert len(frames) <= 256
        print(json.dumps({'received_hex': received.hex(), 'peer': peer, 'capture_interface': 'B/eth0', 'raw_frames': frames}), flush=True)


def decode(frames: list[str]) -> list[dict]:
    rows: list[dict] = []
    for index, raw in enumerate(frames):
        frame = bytes.fromhex(raw)
        if len(frame) < 54 or frame[12:14] != b'\x08\x00' or frame[23] != 6:
            continue
        ip_length = int.from_bytes(frame[16:18])
        ip_header_length = (frame[14] & 15) * 4
        offset = 14 + ip_header_length
        end = 14 + ip_length
        assert ip_header_length >= 20 and offset + 20 <= end <= len(frame)
        assert int.from_bytes(frame[20:22]) & 0x3fff == 0, 'fragmented IPv4 outside scope'
        source = socket.inet_ntoa(frame[26:30])
        destination = socket.inet_ntoa(frame[30:34])
        source_port = int.from_bytes(frame[offset:offset + 2])
        destination_port = int.from_bytes(frame[offset + 2:offset + 4])
        if {source, destination} != {'10.15.0.1', '10.15.0.2'} or 46015 not in (source_port, destination_port):
            continue
        tcp_length = (frame[offset + 12] >> 4) * 4
        end = 14 + ip_length
        assert 20 <= tcp_length <= 60 and offset + tcp_length <= end
        options = frame[offset + 20:offset + tcp_length]
        sacks: list[list[int]] = []
        permitted = False
        cursor = 0
        while cursor < len(options):
            kind = options[cursor]
            if kind == 0:
                break
            if kind == 1:
                cursor += 1
                continue
            assert cursor + 1 < len(options)
            size = options[cursor + 1]
            assert size >= 2 and cursor + size <= len(options)
            if kind == 4:
                assert size == 2
                permitted = True
            if kind == 5:
                assert size >= 10 and (size - 2) % 8 == 0
                sacks.extend([[int.from_bytes(options[pos:pos + 4]), int.from_bytes(options[pos + 4:pos + 8])]
                              for pos in range(cursor + 2, cursor + size, 8)])
            cursor += size
        flags = frame[offset + 13]
        data = frame[offset + tcp_length:end]
        rows.append({'frame_index': index, 'source': source, 'destination': destination,
                     'source_port': source_port, 'destination_port': destination_port,
                     'ip_header_length': ip_header_length, 'tcp_header_length': tcp_length, 'ip_total_length': ip_length,
                     'seq': int.from_bytes(frame[offset + 4:offset + 8]),
                     'ack': int.from_bytes(frame[offset + 8:offset + 12]), 'flags': flags,
                     'data_length': len(data), 'data_hex': data.hex(), 'sack_permitted': permitted,
                     'sack_blocks': sacks, 'sequence_span': len(data) + bool(flags & 2) + bool(flags & 1)})
    initial = {row['source']: row['seq'] for row in rows if row['flags'] & 2}
    assert set(initial) == {'10.15.0.1', '10.15.0.2'}
    for row in rows:
        row['relative_seq'] = (row['seq'] - initial[row['source']]) % (1 << 32)
        peer_isn = initial[row['destination']]
        row['relative_ack'] = (row['ack'] - peer_isn) % (1 << 32) if row['flags'] & 16 else None
        row['relative_sack_blocks'] = [[(left - peer_isn) % (1 << 32), (right - peer_isn) % (1 << 32)]
                                       for left, right in row['sack_blocks']]
    for address in initial:
        fins = [row for row in rows if row['source'] == address and row['flags'] & 1]
        assert fins and all(row['relative_seq'] + row['data_length'] == 65 for row in fins)
        assert any(row['destination'] == address and row['relative_ack'] == 66 for row in rows)
        captured: dict[int, int] = {}
        for row in rows:
            if row['source'] == address:
                for offset, byte in enumerate(bytes.fromhex(row['data_hex']), row['relative_seq']):
                    assert offset not in captured or captured[offset] == byte
                    captured[offset] = byte
        assert bytes(captured[index] for index in range(1, 65)) == PAYLOAD
    return rows


def scenario(reorder: bool) -> None:
    prefix = 'net15-' + uuid.uuid4().hex[:8]
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
            command('ip', '-n', ns, 'address', 'add', f'10.15.0.{host}/24', 'dev', 'eth0')
            command('ip', '-n', ns, 'link', 'set', 'eth0', 'up')
        if reorder:
            command('ip', 'netns', 'exec', a, 'tc', 'qdisc', 'add', 'dev', 'eth0', 'root', 'netem',
                    'limit', '100', 'delay', '100ms', 'reorder', '100%', 'gap', '2')
        script = str(Path(__file__).resolve())
        proc = subprocess.Popen(['ip', 'netns', 'exec', b, sys.executable, script, 'server'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        children.append(proc)
        assert proc.stdout is not None
        if not select.select([proc.stdout], [], [], 5)[0] or proc.stdout.readline().strip() != 'READY':
            raise TimeoutError('capture/server did not become ready')
        sent = json.loads(command('ip', 'netns', 'exec', a, sys.executable, script, 'client'))
        stdout, stderr = proc.communicate(timeout=10)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, proc.args, stderr=stderr)
        received = json.loads(stdout)
        rows = decode(received['raw_frames'])
        sequences = [row['relative_seq'] for row in rows if row['source'] == '10.15.0.1' and row['data_length']]
        print(json.dumps({'case': 'netem-gap2' if reorder else 'baseline', 'prefix': prefix,
                          'client': sent, 'server': received, 'decoded': rows,
                          'client_data_arrival_seq': sequences,
                          'sack_observed': any(row['sack_blocks'] for row in rows),
                          'decreasing_data_seq_observed': any(right < left for left, right in zip(sequences, sequences[1:])),
                          'qdisc': command('ip', 'netns', 'exec', a, 'tc', '-s', 'qdisc', 'show', 'dev', 'eth0') if reorder else None}), flush=True)
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
    parser.add_argument('mode', choices=['lab', 'server', 'client'], nargs='?', default='lab')
    args = parser.parse_args()
    match args.mode:
        case 'client':
            client()
        case 'server':
            server()
        case 'lab':
            if platform.system() != 'Linux' or os.geteuid() != 0:
                raise SystemExit('Requires root in owned Linux VM')
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                              'ip': command('ip', '-V').strip(), 'tc': shutil.which('tc'),
                              'expected_hex': PAYLOAD.hex()}), flush=True)
            scenario(False)
            if shutil.which('tc'):
                scenario(True)
            else:
                print(json.dumps({'skipped': 'netem reordering', 'reason': 'tc unavailable'}))
        case _:
            assert_never(args.mode)


if __name__ == '__main__':
    main()
