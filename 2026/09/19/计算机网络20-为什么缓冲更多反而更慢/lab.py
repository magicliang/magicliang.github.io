#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: sudo python3 lab.py inside the dedicated Linux VM
"""Bounded FIFO/FQ-CoDel comparison with independent UDP probes and ECN evidence."""
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
        if not select.select([proc.stdout], [], [], max(0, deadline - time.monotonic()))[0]: break
        byte = os.read(proc.stdout.fileno(), 1)
        if byte in (b'\n', b''): return data.decode().strip()
        data.extend(byte)
    raise TimeoutError('child response deadline')


def sender() -> None:
    with socket.socket() as connection:
        connection.settimeout(1)
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, b'reno')
        connection.connect(('10.20.2.2', 46020))
        algorithm = connection.getsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, 32).split(b'\0')[0].decode()
        assert algorithm == 'reno'
        deadline, accepted = time.monotonic() + 17, 0
        stop = 'deadline'
        while time.monotonic() < deadline:
            try: accepted += connection.send(b'x' * 65536)
            except TimeoutError: continue
            except (BrokenPipeError, ConnectionResetError) as error:
                stop = type(error).__name__
                break
        print(json.dumps({'algorithm': algorithm, 'accepted_local_bytes': accepted, 'stop': stop}), flush=True)


def receiver() -> None:
    with ExitStack() as resources:
        listener = resources.enter_context(socket.socket())
        listener.bind(('10.20.2.2', 46020)); listener.listen(1)
        udp = resources.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        udp.bind(('10.20.2.2', 46021))
        start = time.monotonic_ns()
        end = start + 18_000_000_000
        print(json.dumps({'start_ns': start, 'load_start_ns': start + 3_000_000_000,
                          'measure_start_ns': start + 6_000_000_000, 'end_ns': end}), flush=True)
        inputs, counted, total = [listener, udp], 0, 0
        while time.monotonic_ns() < end:
            for ready in select.select(inputs, [], [], min(0.1, max(0, (end - time.monotonic_ns()) / 1e9)))[0]:
                if ready is listener:
                    stream, _ = listener.accept(); resources.enter_context(stream)
                    inputs.remove(listener); inputs.append(stream)
                elif ready is udp:
                    data, address = udp.recvfrom(128); udp.sendto(data, address)
                else:
                    block = ready.recv(65536); sampled = time.monotonic_ns()
                    assert block and block == b'x' * len(block)
                    total += len(block)
                    if start + 6_000_000_000 <= sampled < end: counted += len(block)
        assert counted > 0
        print(json.dumps({'measured_bytes': counted, 'total_received_bytes': total,
                          'goodput_mbit_s': counted * 8 / 12 / 1e6, 'finished_ns': time.monotonic_ns()}), flush=True)


def probe(end: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.connect(('10.20.2.2', 46021)); udp.settimeout(1.0)
        observations = []
        next_sample = time.monotonic()
        for sequence in range(100):
            if time.monotonic_ns() >= end - 1_000_000_000: break
            payload = sequence.to_bytes(4, 'big')
            started = time.monotonic_ns(); udp.send(payload)
            rtt = None
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                udp.settimeout(max(0.001, deadline - time.monotonic()))
                try: echoed = udp.recv(128)
                except TimeoutError: break
                if echoed == payload:
                    rtt = (time.monotonic_ns() - started) / 1e6
                    break
            observations.append({'sequence': sequence, 'time_ns': started, 'rtt_ms': rtt})
            next_sample = max(next_sample + 0.2, time.monotonic())
            time.sleep(max(0, next_sample - time.monotonic()))
        print(json.dumps(observations), flush=True)


def capture() -> None:
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as packets:
        packets.bind(('eth0', 0)); print('READY', flush=True)
        counts = {'syn': 0, 'ce': 0, 'ece': 0, 'cwr': 0}
        evidence = []
        deadline, total = time.monotonic() + 25, 0
        while time.monotonic() < deadline:
            ready = select.select([packets, sys.stdin], [], [], max(0, deadline - time.monotonic()))[0]
            if packets in ready:
                frame = packets.recv(65535); total += 1
                assert total <= 50000
                if len(frame) >= 54 and frame[12:14] == b'\x08\x00' and frame[23] == 6:
                    offset = 14 + (frame[14] & 15) * 4
                    assert offset >= 34 and offset + 20 <= len(frame)
                    sport, dport = int.from_bytes(frame[offset:offset + 2]), int.from_bytes(frame[offset + 2:offset + 4])
                    if 46020 in (sport, dport):
                        flags, ecn = frame[offset + 13], frame[15] & 3
                        kinds = [k for k, enabled in (('syn', flags & 2), ('ce', ecn == 3),
                                  ('ece', flags & 64 and not flags & 2), ('cwr', flags & 128 and not flags & 2)) if enabled]
                        keep = any(counts[k] < (4 if k == 'syn' else 1) for k in kinds)
                        for kind in kinds: counts[kind] += 1
                        if keep: evidence.append({'time_ns': time.monotonic_ns(), 'kinds': kinds, 'hex': frame.hex(),
                            'source': socket.inet_ntoa(frame[26:30]), 'source_port': sport, 'destination_port': dport,
                            'seq': int.from_bytes(frame[offset + 4:offset + 8]), 'ack': int.from_bytes(frame[offset + 8:offset + 12]), 'flags': flags, 'ip_ecn': ecn})
            if sys.stdin in ready:
                assert sys.stdin.readline().strip() == 'STOP'
                print(json.dumps({'counts': counts, 'evidence': evidence, 'total_frames_seen': total}), flush=True)
                return
        raise TimeoutError('capture deadline')


def scenario(fq: bool, repeat: int) -> None:
    prefix = 'net20-' + uuid.uuid4().hex[:8]
    a, r, b = (prefix + '-' + role for role in ('a', 'r', 'b'))
    owned, children = [], []
    try:
        for ns in (a, r, b): command('ip', 'netns', 'add', ns); owned.append(ns)
        for end, interface in ((a, 'left'), (b, 'right')):
            command('ip', '-n', end, 'link', 'add', 'eth0', 'type', 'veth', 'peer', 'name', interface)
            command('ip', '-n', end, 'link', 'set', interface, 'netns', r)
        for ns, interface, ip in ((a, 'eth0', '10.20.1.2/24'), (r, 'left', '10.20.1.1/24'), (r, 'right', '10.20.2.1/24'), (b, 'eth0', '10.20.2.2/24')):
            command('ip', '-n', ns, 'address', 'add', ip, 'dev', interface)
            command('ip', '-n', ns, 'link', 'set', interface, 'up')
        command('ip', '-n', a, 'route', 'add', 'default', 'via', '10.20.1.1')
        command('ip', '-n', b, 'route', 'add', 'default', 'via', '10.20.2.1')
        command('ip', 'netns', 'exec', r, 'sysctl', '-w', 'net.ipv4.ip_forward=1')
        ecn = {ns: command('ip', 'netns', 'exec', ns, 'sysctl', '-w', 'net.ipv4.tcp_ecn=1') for ns in (a, b)}
        parent = ['tc', 'qdisc', 'add', 'dev', 'right', 'root', 'handle', '1:', 'tbf', 'rate', '5mbit', 'burst', '16kb', 'limit', '64kb']
        child = ['tc', 'qdisc', 'add', 'dev', 'right', 'parent', '1:1', 'handle', '10:'] + (['fq_codel', 'limit', '256', 'memory_limit', '1048576', 'target', '5ms', 'interval', '100ms', 'ecn'] if fq else ['pfifo', 'limit', '256'])
        for config in (parent, child): command('ip', 'netns', 'exec', r, *config)
        stats = ['ip', 'netns', 'exec', r, 'tc', '-s', '-d', 'qdisc', 'show', 'dev', 'right']
        before = command(*stats)
        for ns, mode in ((b, 'capture'), (b, 'receiver')):
            proc = subprocess.Popen(['ip', 'netns', 'exec', ns, sys.executable, str(Path(__file__).resolve()), mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            children.append(proc)
        watcher, server = children
        ready = read(watcher); assert ready == 'READY'
        interval = json.loads(read(server))
        prober = subprocess.Popen(['ip', 'netns', 'exec', a, sys.executable, str(Path(__file__).resolve()), 'probe', '--end-ns', str(interval['end_ns'])], stdout=subprocess.PIPE, text=True)
        children.append(prober)
        time.sleep(max(0, (interval['load_start_ns'] - time.monotonic_ns()) / 1e9))
        client = subprocess.Popen(['ip', 'netns', 'exec', a, sys.executable, str(Path(__file__).resolve()), 'sender'], stdout=subprocess.PIPE, text=True)
        children.append(client)
        samples, next_sample = [], time.monotonic()
        while time.monotonic_ns() < interval['end_ns']:
            started = time.monotonic_ns()
            raw = command('ip', 'netns', 'exec', a, 'ss', '-tinm', 'dst 10.20.2.2 dport = :46020')
            samples.append({'start_ns': started, 'end_ns': time.monotonic_ns(), 'ss': raw}); next_sample += 0.2
            time.sleep(max(0, min(next_sample - time.monotonic(), (interval['end_ns'] - time.monotonic_ns()) / 1e9)))
        received, probes, sent = json.loads(read(server)), json.loads(read(prober)), json.loads(read(client))
        after = command(*stats)
        assert watcher.stdin is not None
        watcher.stdin.write('STOP\n'); watcher.stdin.flush()
        captured = json.loads(read(watcher))
        assert any(e['flags'] & 0xC2 == 0xC2 for e in captured['evidence'])
        assert any(e['flags'] & 0x52 == 0x52 for e in captured['evidence'])
        summary = {}
        for phase, low, high in (('baseline', interval['start_ns'], interval['load_start_ns']), ('loaded', interval['measure_start_ns'], interval['end_ns'])):
            points = [p for p in probes if low <= p['time_ns'] < high]
            values = sorted(p['rtt_ms'] for p in points if p['rtt_ms'] is not None)
            summary[phase] = {'sent': len(points), 'timeouts': len(points) - len(values), 'p50_ms': values[(len(values)-1)//2] if values else None, 'p95_ms': values[max(0, (95*len(values)+99)//100-1)] if values else None}
        print(json.dumps({'policy': 'fq_codel' if fq else 'pfifo', 'repeat': repeat, 'prefix': prefix, 'ecn_sysctl': ecn, 'parent_command': parent, 'child_command': child, 'qdisc_before': before, 'qdisc_after': after, 'interval': interval, 'receiver': received, 'sender': sent, 'probes': probes, 'probe_summary': summary, 'ss_samples': samples, 'capture': captured}), flush=True)
    finally:
        for child_proc in children:
            if child_proc.poll() is None: child_proc.terminate()
            try: child_proc.wait(timeout=3)
            except subprocess.TimeoutExpired: child_proc.kill(); child_proc.wait(timeout=3)
        for ns in reversed(owned): command('ip', 'netns', 'delete', ns)
        assert not any(ns in command('ip', 'netns', 'list') for ns in owned)
        print(json.dumps({'cleanup': owned}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['lab', 'sender', 'receiver', 'probe', 'capture'], nargs='?', default='lab')
    parser.add_argument('--end-ns', type=int, default=0)
    args = parser.parse_args()
    if args.mode == 'probe' and args.end_ns <= 0: parser.error('probe requires positive --end-ns')
    if platform.system() != 'Linux' or os.geteuid() != 0: raise SystemExit('Requires root in owned Linux VM')
    match args.mode:
        case 'sender': sender()
        case 'receiver': receiver()
        case 'probe': probe(args.end_ns)
        case 'capture': capture()
        case 'lab':
            print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(), 'tc': command('tc', '-V'), 'ss': command('ss', '-V'), 'algorithms': command('cat', '/proc/sys/net/ipv4/tcp_available_congestion_control')}), flush=True)
            for repeat in range(1, 4):
                for fq in (False, True): scenario(fq, repeat)
        case _: assert_never(args.mode)


if __name__ == '__main__': main()
