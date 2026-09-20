#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py in an owned Linux VM
"""Six bounded Reno runs through one isolated 5mbit TBF; receive-byte goodput."""
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
from contextlib import ExitStack
from pathlib import Path
from typing import assert_never


def command(*args: str) -> str:
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, text=True, timeout=10).stdout


def read(proc: subprocess.Popen[str]) -> str:
    assert proc.stdout is not None
    data = bytearray()
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if not select.select([proc.stdout], [], [], max(0, deadline - time.monotonic()))[0]:
            break
        byte = os.read(proc.stdout.fileno(), 1)
        if byte in (b'\n', b''):
            return data.decode().strip()
        data.extend(byte)
    raise TimeoutError('child message deadline')


def signal(proc: subprocess.Popen[str]) -> None:
    assert proc.stdin is not None
    proc.stdin.write('GO\n')
    proc.stdin.flush()


def barrier() -> None:
    if not select.select([sys.stdin], [], [], 10)[0]:
        raise TimeoutError('start barrier')
    assert sys.stdin.readline().strip() == 'GO'


def sender() -> None:
    with socket.socket() as connection:
        connection.settimeout(1)
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, b'reno')
        connection.connect(('10.19.2.2', 46019))
        algorithm = connection.getsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, 32).split(b'\0')[0].decode()
        assert algorithm == 'reno'
        print(json.dumps({'algorithm': algorithm, 'local': connection.getsockname()}), flush=True)
        barrier()
        deadline = time.monotonic() + 18
        block = b'x' * 65536
        accepted = 0
        stopped = 'deadline'
        while time.monotonic() < deadline:
            try:
                accepted += connection.send(block)
            except TimeoutError:
                continue
            except (BrokenPipeError, ConnectionResetError) as error:
                stopped = type(error).__name__
                break
        print(json.dumps({'accepted_local_bytes': accepted, 'stopped': stopped,
                          'finished_ns': time.monotonic_ns()}), flush=True)


def receiver(flows: int) -> None:
    with ExitStack() as resources:
        listener = resources.enter_context(socket.socket())
        listener.settimeout(10)
        listener.bind(('10.19.2.2', 46019))
        listener.listen(2)
        print('LISTEN', flush=True)
        connections = []
        for _ in range(flows):
            connection, _ = listener.accept()
            resources.enter_context(connection)
            connections.append(connection)
        print('CONNECTED', flush=True)
        barrier()
        start = time.monotonic_ns()
        measured_start, end = start + 3_000_000_000, start + 15_000_000_000
        print(json.dumps({'start_ns': start, 'measured_start_ns': measured_start, 'end_ns': end}), flush=True)
        counted, total = [0] * flows, [0] * flows
        peers = [connection.getpeername() for connection in connections]
        while time.monotonic_ns() < end:
            ready = select.select(connections, [], [], min(0.1, max(0, (end - time.monotonic_ns()) / 1e9)))[0]
            for connection in ready:
                block = connection.recv(65536)
                sampled = time.monotonic_ns()
                assert block and block == b'x' * len(block)
                index = connections.index(connection)
                total[index] += len(block)
                if measured_start <= sampled < end:
                    counted[index] += len(block)
        goodput = [value * 8 / 12 / 1e6 for value in counted]
        assert all(value > 0 for value in counted)
        jain = sum(counted) ** 2 / (flows * sum(value * value for value in counted))
        print(json.dumps({'peers': peers, 'measured_bytes': counted, 'total_received_bytes': total,
                          'goodput_mbit_s': goodput, 'jain': jain, 'finished_ns': time.monotonic_ns(),
                          'all_received_content_checked': True}), flush=True)


def scenario(flows: int, repeat: int) -> None:
    prefix = 'net19-' + uuid.uuid4().hex[:8]
    a, r, b = (prefix + '-' + role for role in ('a', 'r', 'b'))
    owned: list[str] = []
    children: list[subprocess.Popen[str]] = []
    try:
        for ns in (a, r, b):
            command('ip', 'netns', 'add', ns)
            owned.append(ns)
        for end, interface in ((a, 'left'), (b, 'right')):
            command('ip', '-n', end, 'link', 'add', 'eth0', 'type', 'veth', 'peer', 'name', interface)
            command('ip', '-n', end, 'link', 'set', interface, 'netns', r)
        for ns, interface, ip in ((a, 'eth0', '10.19.1.2/24'), (r, 'left', '10.19.1.1/24'),
                                  (r, 'right', '10.19.2.1/24'), (b, 'eth0', '10.19.2.2/24')):
            command('ip', '-n', ns, 'address', 'add', ip, 'dev', interface)
            command('ip', '-n', ns, 'link', 'set', interface, 'up')
        command('ip', '-n', a, 'route', 'add', 'default', 'via', '10.19.1.1')
        command('ip', '-n', b, 'route', 'add', 'default', 'via', '10.19.2.1')
        command('ip', 'netns', 'exec', r, 'sysctl', '-w', 'net.ipv4.ip_forward=1')
        tbf = ['tc', 'qdisc', 'add', 'dev', 'right', 'root', 'tbf', 'rate', '5mbit', 'burst', '16kb', 'limit', '64kb']
        command('ip', 'netns', 'exec', r, *tbf)
        stats = ['ip', 'netns', 'exec', r, 'tc', '-s', '-d', 'qdisc', 'show', 'dev', 'right']
        before = command(*stats)
        configurations = []
        for ns, mode in [(b, 'receiver')] + [(a, 'sender')] * flows:
            proc = subprocess.Popen(['ip', 'netns', 'exec', ns, sys.executable, str(Path(__file__).resolve()), mode, '--flows', str(flows)],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            children.append(proc)
            line = read(proc)
            if mode == 'receiver':
                assert line == 'LISTEN'
            else:
                configurations.append(json.loads(line))
        server = children[0]
        ready = read(server)
        assert ready == 'CONNECTED'
        signal(server)
        interval = json.loads(read(server))
        for child in children[1:]:
            signal(child)
        samples = []
        next_sample = time.monotonic()
        while time.monotonic_ns() < interval['end_ns']:
            started = time.monotonic_ns()
            raw = command('ip', 'netns', 'exec', a, 'ss', '-tinm', 'dst 10.19.2.2 dport = :46019')
            samples.append({'start_ns': started, 'end_ns': time.monotonic_ns(), 'ss': raw})
            next_sample += 0.2
            time.sleep(max(0, min(next_sample - time.monotonic(), (interval['end_ns'] - time.monotonic_ns()) / 1e9)))
        result = json.loads(read(server))
        after = command(*stats)
        senders = [json.loads(read(child)) for child in children[1:]]
        print(json.dumps({'flows': flows, 'repeat': repeat, 'prefix': prefix, 'tbf_command': tbf,
                          'tbf_before': before, 'tbf_after': after, 'sender_configuration': configurations,
                          'interval': interval, 'receiver': result, 'senders': senders, 'samples': samples}), flush=True)
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
    parser.add_argument('mode', choices=['lab', 'sender', 'receiver'], nargs='?', default='lab')
    parser.add_argument('--flows', type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        raise SystemExit('Requires root in owned Linux VM')
    match args.mode:
        case 'sender': sender()
        case 'receiver': receiver(args.flows)
        case 'lab':
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                              'tc': command('tc', '-V'), 'ss': command('ss', '-V'),
                              'available_algorithms': command('cat', '/proc/sys/net/ipv4/tcp_available_congestion_control'),
                              'allowed_algorithms': command('cat', '/proc/sys/net/ipv4/tcp_allowed_congestion_control')}), flush=True)
            for repeat in range(1, 4):
                for flows in (1, 2):
                    scenario(flows, repeat)
        case _: assert_never(args.mode)


if __name__ == '__main__':
    main()
