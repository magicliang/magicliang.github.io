#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 lab.py (installed unbound/unbound-checkconf and dig required)
"""Loopback-only Unbound stub-cache experiment; bounded teaching authoritative wire subset."""
import argparse
import json
import platform
import re
import select
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


class WireError(Exception):
    """Malformed or unsupported DNS question."""


@dataclass(frozen=True, slots=True)
class State:
    """Mutable zone and query log intentionally synchronized under one lock."""
    records: dict[str, str] = field(default_factory=lambda: {'www.lab.test.': '192.0.2.1', 'ns.lab.test.': '127.0.0.1'})
    events: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


def name_wire(name: str) -> bytes:
    if name == '.': return b'\0'
    return b''.join(bytes([len(part)]) + part.encode('ascii') for part in name.rstrip('.').split('.')) + b'\0'


def question(message: bytes) -> tuple[str, int, bytes]:
    if not 12 <= len(message) <= 4096 or struct.unpack('!H', message[4:6])[0] != 1:
        raise WireError('one bounded question required')
    if int.from_bytes(message[2:4]) & 0xF800: raise WireError('query opcode only')
    labels, cursor, resume, pointers, visited = [], 12, None, 0, set()
    while True:
        if cursor >= len(message) or cursor in visited: raise WireError('name bounds or cycle')
        visited.add(cursor); size = message[cursor]
        if size & 0xC0 == 0xC0:
            if cursor + 1 >= len(message) or pointers >= 16: raise WireError('pointer bounds')
            if resume is None: resume = cursor + 2
            cursor = ((size & 63) << 8) | message[cursor + 1]; pointers += 1
            continue
        if size > 63 or cursor + 1 + size > len(message): raise WireError('label bounds')
        cursor += 1
        if size == 0: break
        labels.append(message[cursor:cursor + size].decode('ascii').lower()); cursor += size
        if sum(len(label) + 1 for label in labels) > 254: raise WireError('expanded name bounds')
    end = cursor if resume is None else resume
    if end + 4 > len(message): raise WireError('question tail bounds')
    qtype, qclass = struct.unpack('!HH', message[end:end + 4])
    if qclass != 1: raise WireError('IN only')
    name = '.'.join(labels) + '.'
    return name, qtype, name_wire(name) + struct.pack('!HH', qtype, qclass)


def rr(owner: str, kind: int, data: bytes) -> bytes:
    return name_wire(owner) + struct.pack('!HHIH', kind, 1, 3, len(data)) + data


def answer(message: bytes, state: State, transport: str) -> bytes:
    name, qtype, query = question(message)
    with state.lock:
        answer_data, authority, rcode = b'', b'', 0
        local = name == 'lab.test.' or name.endswith('.lab.test.')
        soa = rr('lab.test.', 6, name_wire('ns.lab.test.') + name_wire('hostmaster.lab.test.') + struct.pack('!IIIII', 1, 60, 30, 300, 3))
        if not local: rcode = 5
        elif name in state.records and qtype == 1: answer_data = rr(name, 1, socket.inet_aton(state.records[name]))
        elif name == 'lab.test.' and qtype == 6: answer_data = soa
        elif name == 'lab.test.' and qtype == 2: answer_data = rr(name, 2, name_wire('ns.lab.test.'))
        else:
            rcode = 0 if name in state.records or name == 'lab.test.' else 3
            authority = soa
        flags = 0x8000 | (0x0400 if local else 0) | (int.from_bytes(message[2:4]) & 0x0100) | rcode
        response = message[:2] + struct.pack('!HHHHH', flags, 1, bool(answer_data), bool(authority), 0) + query + answer_data + authority
        state.events.append({'time_ns': time.monotonic_ns(), 'name': name, 'type': qtype, 'transport': transport,
                             'rcode': rcode, 'query_hex': message.hex(), 'response_hex': response.hex()})
        assert len(state.events) <= 100
        return response


def exact(connection: socket.socket, count: int) -> bytes:
    data = b''
    while len(data) < count:
        part = connection.recv(count - len(data))
        if not part: raise WireError('short TCP input')
        data += part
    return data


def serve(sockets: tuple[socket.socket, socket.socket], state: State, stop: threading.Event) -> None:
    udp, tcp = sockets
    deadline = time.monotonic() + 60
    while not stop.is_set() and time.monotonic() < deadline:
        for ready in select.select(sockets, [], [], 0.1)[0]:
            try:
                if ready is udp:
                    data, peer = udp.recvfrom(4097)
                    udp.sendto(answer(data, state, 'udp'), peer)
                else:
                    connection, _ = tcp.accept()
                    with connection:
                        connection.settimeout(2)
                        size = int.from_bytes(exact(connection, 2))
                        if not 12 <= size <= 4096: raise WireError('TCP length bounds')
                        result = answer(exact(connection, size), state, 'tcp')
                        connection.sendall(len(result).to_bytes(2) + result)
            except (WireError, UnicodeDecodeError, TimeoutError) as error:
                with state.lock: state.events.append({'rejected': str(error), 'time_ns': time.monotonic_ns()})


def query(port: int, name: str, options: tuple[str, ...] = ('A',)) -> str:
    return subprocess.run(['/usr/bin/dig', '@127.0.0.1', '-p', str(port), name, *options, '+tries=1', '+time=2', '+noedns'],
                          check=True, capture_output=True, text=True, timeout=4).stdout


def wait_expiry(start: int) -> None:
    deadline = start + 4_100_000_000
    time.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9))


def lab() -> None:
    unbound, checker = shutil.which('unbound'), shutil.which('unbound-checkconf')
    if not unbound or not checker: raise SystemExit('installed unbound and unbound-checkconf required')
    state, stop = State(), threading.Event()
    with tempfile.TemporaryDirectory(prefix='net21-') as directory, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp, socket.socket() as tcp:
        udp.bind(('127.0.0.1', 0)); auth_port = udp.getsockname()[1]
        tcp.bind(('127.0.0.1', auth_port)); tcp.listen(4)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); resolver_port = reservation.getsockname()[1]
        config = f'''server:
  interface: 127.0.0.1@{resolver_port}
  outgoing-interface: 127.0.0.1
  do-ip6: no
  chroot: ""
  username: ""
  directory: "{directory}"
  pidfile: ""
  use-syslog: no
  module-config: "iterator"
  do-not-query-localhost: no
  prefetch: no
  serve-expired: no
  cache-min-ttl: 0
  cache-max-negative-ttl: 3
  local-zone: "." refuse
  local-zone: "test." nodefault
  local-zone: "lab.test." transparent
stub-zone:
  name: "lab.test."
  stub-addr: 127.0.0.1@{auth_port}
  stub-prime: no
  stub-first: no
'''
        config_path = Path(directory) / 'unbound.conf'; config_path.write_text(config)
        checked = subprocess.run([checker, str(config_path)], check=True, capture_output=True, text=True, timeout=5).stdout
        print(json.dumps({'environment': platform.platform(), 'unbound': subprocess.run([unbound, '-V'], capture_output=True, text=True, timeout=5).stdout,
                          'config': config, 'checkconf': checked}), flush=True)
        worker = threading.Thread(target=serve, args=((udp, tcp), state, stop)); worker.start()
        with (Path(directory) / 'unbound.log').open('w+') as logfile:
            proc = subprocess.Popen([unbound, '-d', '-p', '-c', str(config_path)], stdout=logfile, stderr=logfile)
            try:
                ready = False
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if proc.poll() is not None: raise WireError('Unbound startup failed')
                    try:
                        with socket.create_connection(('127.0.0.1', resolver_port), timeout=0.1): ready = True
                        break
                    except ConnectionRefusedError: time.sleep(0.05)
                assert ready
                direct = subprocess.run(['/usr/bin/dig', '@127.0.0.1', '-p', str(auth_port), 'www.lab.test.', 'A', '+tcp', '+noedns', '+time=2', '+tries=1'], check=True, capture_output=True, text=True, timeout=4).stdout
                assert '192.0.2.1' in direct
                print(json.dumps({'stage': 'direct-authority-tcp', 'dig': direct}), flush=True)
                stages = [('cold', 'www.lab.test.', '192.0.2.1', True), ('hit', 'www.lab.test.', '192.0.2.1', False),
                          ('modified-cached', 'www.lab.test.', '192.0.2.1', False), ('expired-positive', 'www.lab.test.', '192.0.2.2', True),
                          ('negative-cold', 'missing.lab.test.', 'NXDOMAIN', True), ('negative-hit', 'missing.lab.test.', 'NXDOMAIN', False),
                          ('created-cached', 'missing.lab.test.', 'NXDOMAIN', False), ('expired-negative', 'missing.lab.test.', '192.0.2.3', True)]
                anchor = 0
                for stage, name, expected, upstream in stages:
                    if stage == 'modified-cached':
                        with state.lock: state.records[name] = '192.0.2.2'
                    if stage == 'created-cached':
                        with state.lock: state.records[name] = '192.0.2.3'
                    if stage in ('modified-cached', 'created-cached'):
                        direct = query(auth_port, name, ('A', '+norecurse'))
                        wanted = '192.0.2.2' if stage == 'modified-cached' else '192.0.2.3'
                        assert wanted in direct and ' aa;' in direct
                        print(json.dumps({'stage': 'direct-' + stage, 'dig': direct}), flush=True)
                    if stage.startswith('expired'): wait_expiry(anchor)
                    with state.lock: before = len(state.events)
                    output = query(resolver_port, name)
                    after_ns = time.monotonic_ns()
                    with state.lock: after = len(state.events)
                    assert expected in output and (after > before if upstream else after == before)
                    if stage in ('cold', 'negative-cold'): anchor = after_ns
                    print(json.dumps({'stage': stage, 'time_ns': after_ns, 'auth_before': before, 'auth_after': after, 'dig': output}), flush=True)
                output = query(resolver_port, 'www.lab.test.', ('AAAA',))
                assert 'status: NOERROR' in output and 'ANSWER: 0' in output and 'SOA' in output
                print(json.dumps({'stage': 'nodata-existing-AAAA', 'dig': output}), flush=True)
                output = query(resolver_port, 'www.lab.test.')
                assert '192.0.2.2' in output and 'status: NOERROR' in output
                print(json.dumps({'stage': 'A-after-nodata', 'dig': output}), flush=True)
                with state.lock: before = len(state.events)
                output = query(resolver_port, 'outside.example.')
                with state.lock: after = len(state.events)
                assert 'status: REFUSED' in output and before == after
                print(json.dumps({'stage': 'outside-resolver-refused', 'auth_before': before, 'auth_after': after, 'dig': output}), flush=True)
                output = query(auth_port, 'outside.example.')
                assert 'status: REFUSED' in output
                print(json.dumps({'stage': 'outside-authority-refused', 'dig': output}), flush=True)
            finally:
                if proc.poll() is None: proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)
                stop.set(); worker.join(timeout=3)
                assert not worker.is_alive()
                logfile.seek(0)
                print(json.dumps({'authority_queries': state.events, 'unbound_log': logfile.read(), 'owned_process_stopped': proc.returncode, 'authority_thread_stopped': True}), flush=True)
    print(json.dumps({'temporary_directory_removed': not Path(directory).exists()}), flush=True)


def self_check() -> None:
    header = struct.pack('!HHHHHH', 1, 0x100, 1, 0, 0, 0)
    valid = header + name_wire('www.lab.test.') + struct.pack('!HH', 1, 1)
    parsed = question(valid)
    assert parsed[:2] == ('www.lab.test.', 1)
    for malformed in (b'', valid[:-1], header + b'\xc0\x0c\0\1\0\1', valid + b'x' * 4096):
        try: question(malformed)
        except WireError: continue
        raise AssertionError('malformed question accepted')
    state = State()
    nodata = answer(header + name_wire('www.lab.test.') + struct.pack('!HH', 28, 1), state, 'self-check')
    refused = answer(header + name_wire('outside.example.') + struct.pack('!HH', 1, 1), state, 'self-check')
    assert int.from_bytes(nodata[2:4]) & 15 == 0 and int.from_bytes(nodata[6:8]) == 0 and int.from_bytes(nodata[8:10]) == 1
    assert int.from_bytes(refused[2:4]) & 15 == 5 and not int.from_bytes(refused[2:4]) & 0x400
    print('self-check: normal question, four malformed inputs, NODATA and REFUSED passed')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    if args.self_check: self_check()
    else: lab()


if __name__ == '__main__': main()
