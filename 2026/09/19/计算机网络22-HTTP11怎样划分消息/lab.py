#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 lab.py; python3 lab.py --self-check (offline only)
"""Bounded HTTP/1.1 framing subset, real loopback reuse and separately labelled offline splits."""
import argparse
import json
import platform
import re
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

FIXED: Final = b'HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello'
CHUNKED: Final = (b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nTrailer: X-Lab\r\nConnection: close\r\n\r\n'
                  b'2\r\nwo\r\n3\r\nrld\r\n0\r\nX-Lab: done\r\n\r\n')
AMBIGUOUS: Final = b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n'


class FramingError(Exception):
    """Input is incomplete, malformed, oversized or outside this teaching subset."""


@dataclass(frozen=True, slots=True)
class Reader:
    """Mutable input buffer preserves bytes belonging to following messages."""
    source: Callable[[], bytes]
    buffer: bytearray = field(default_factory=bytearray)
    pulls: list[bytes] = field(default_factory=list)

    def fill(self) -> None:
        block = self.source(); self.pulls.append(block)
        if not block: raise FramingError('unexpected EOF')
        if len(self.buffer) + len(block) > 131072: raise FramingError('buffer limit')
        self.buffer.extend(block)

    def take(self, size: int) -> bytes:
        if not 0 <= size <= 65536: raise FramingError('body/chunk limit')
        while len(self.buffer) < size: self.fill()
        result = bytes(self.buffer[:size]); del self.buffer[:size]
        return result

    def line(self) -> bytes:
        while True:
            index = self.buffer.find(b'\r\n')
            if index >= 0:
                if index > 8192: raise FramingError('line limit')
                result = self.take(index + 2)[:-2]
                if b'\r' in result or b'\n' in result: raise FramingError('CRLF required')
                return result
            if b'\n' in self.buffer: raise FramingError('CRLF required')
            if len(self.buffer) > 8192: raise FramingError('line limit')
            self.fill()


def fields(reader: Reader) -> tuple[tuple[str, str], ...]:
    result, used = [], 0
    for _ in range(33):
        line = reader.line(); used += len(line) + 2
        if used > 8192: raise FramingError('field section limit')
        if not line: return tuple(result)
        match = re.fullmatch(rb"([!#$%&'*+.^_`|~0-9A-Za-z-]+):[ \t]*([\x20-\x7e\t]*)", line)
        if match is None: raise FramingError('field syntax/obs-fold rejected')
        name, value = match[1].decode().lower(), match[2].decode().strip(' \t')
        if any(key == name for key, _ in result): raise FramingError('duplicate field rejected')
        result.append((name, value))
    raise FramingError('field count limit')


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    trailers: tuple[tuple[str, str], ...] = ()


def response(reader: Reader, method: str = 'GET') -> Response:
    if method not in ('GET', 'HEAD'): raise FramingError('method outside subset')
    status_line = reader.line()
    match = re.fullmatch(rb'HTTP/1\.1 ([0-9]{3}) [\x20-\x7e]*', status_line)
    if match is None: raise FramingError('status syntax')
    status, header_fields = int(match[1]), fields(reader)
    headers = dict(header_fields)
    if method == 'HEAD' or 100 <= status < 200 or status in (204, 304):
        return Response(status, header_fields, b'')
    if 'content-length' in headers and 'transfer-encoding' in headers:
        raise FramingError('Content-Length plus Transfer-Encoding rejected')
    if 'transfer-encoding' in headers:
        if headers['transfer-encoding'].lower() != 'chunked': raise FramingError('unsupported transfer coding')
        body = bytearray()
        for _ in range(128):
            size_line = reader.line()
            if re.fullmatch(rb'[0-9A-Fa-f]{1,8}', size_line) is None: raise FramingError('chunk size/extensions outside subset')
            size = int(size_line, 16)
            if size == 0:
                trailers = fields(reader)
                if any(key != 'x-lab' for key, _ in trailers): raise FramingError('trailer outside allowlist')
                return Response(status, header_fields, bytes(body), trailers)
            if len(body) + size > 65536: raise FramingError('body limit')
            body.extend(reader.take(size))
            terminator = reader.take(2)
            if terminator != b'\r\n': raise FramingError('chunk CRLF required')
        raise FramingError('chunk count limit')
    if 'content-length' in headers:
        text = headers['content-length']
        if re.fullmatch(r'[0-9]{1,8}', text) is None: raise FramingError('invalid Content-Length')
        return Response(status, header_fields, reader.take(int(text)))
    raise FramingError('close-delimited body outside subset')


def offline(data: bytes, width: int) -> Reader:
    chunks = iter(data[index:index + width] for index in range(0, len(data), width))
    return Reader(lambda: next(chunks, b''))


def self_check() -> None:
    for width in (1, 2, 7, len(FIXED + CHUNKED)):
        reader = offline(FIXED + CHUNKED, width)
        first = response(reader); remainder = bytes(reader.buffer)
        second = response(reader)
        assert first.body == b'hello' and second.body == b'world' and second.trailers == (('x-lab', 'done'),)
        assert not reader.buffer
        if width == len(FIXED + CHUNKED): assert remainder == CHUNKED
        print(json.dumps({'verification': 'offline-input-splits-not-TCP-segments', 'width': width, 'bodies': ['hello', 'world'], 'remaining_after_first_hex': remainder.hex()}))
    head = offline(b'HTTP/1.1 200 OK\r\nContent-Length: 999\r\n\r\n' + FIXED, 7)
    head_result, after_head = response(head, 'HEAD'), response(head)
    assert head_result.body == b'' and after_head.body == b'hello'
    invalid = {'CL-and-TE': AMBIGUOUS, 'truncated-CL': FIXED[:-1], 'missing-chunk-final-empty-line': CHUNKED[:-2],
               'bare-LF': FIXED.replace(b'\r\n', b'\n'), 'duplicate-CL': FIXED.replace(b'Content-Length: 5', b'Content-Length: 5\r\nContent-Length: 5'),
               'oversized-CL': FIXED.replace(b'Content-Length: 5', b'Content-Length: 99999999')}
    for label, data in invalid.items():
        try: response(offline(data, 2))
        except FramingError as error: print(json.dumps({'verification': 'offline-rejection', 'case': label, 'error': str(error)}))
        else: raise AssertionError(f'accepted {label}')
    print(json.dumps({'verification': 'offline-HEAD-no-body-precedence', 'passed': True}))


def serve(listener: socket.socket, bad: bool, records: list) -> None:
    try:
        connection, peer = listener.accept()
        with connection:
            connection.settimeout(3)
            reader = Reader(lambda: connection.recv(4096))
            methods = []
            for expected in (('/bad',) if bad else ('/fixed', '/chunked')):
                line = reader.line(); headers = dict(fields(reader))
                assert line == f'GET {expected} HTTP/1.1'.encode() and 'host' in headers
                methods.append(line.decode())
            sent = AMBIGUOUS if bad else FIXED + CHUNKED
            connection.sendall(sent)
            if bad:
                try: closed = {'received_after_response_hex': connection.recv(1).hex()}
                except ConnectionResetError as error: closed = {'peer_reset_errno': error.errno}
            else: closed = {'server_closes_after_second_response': True}
            records.append({'accept_count': 1, 'peer': peer, 'methods': methods, 'request_recv_calls': len(reader.pulls),
                            'request_recv_hex': [chunk.hex() for chunk in reader.pulls], 'sent_hex': sent.hex(),
                            'SO_KEEPALIVE': connection.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE), **closed})
    except (OSError, FramingError, AssertionError) as error:
        records.append({'server_error': repr(error)})


def network_case(bad: bool) -> None:
    records = []
    with socket.socket() as listener:
        listener.settimeout(3); listener.bind(('127.0.0.1', 0)); listener.listen(1)
        worker = threading.Thread(target=serve, args=(listener, bad, records)); worker.start()
        try:
            with socket.create_connection(listener.getsockname(), timeout=3) as connection:
                connection.settimeout(3)
                paths = ('/bad',) if bad else ('/fixed', '/chunked')
                request = b''.join(f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{listener.getsockname()[1]}\r\n\r\n'.encode() for path in paths)
                connection.sendall(request)
                reader = Reader(lambda: connection.recv(4096))
                client = {'SO_KEEPALIVE': connection.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE), 'sent_hex': request.hex()}
                if bad:
                    try: response(reader)
                    except FramingError as error: client['rejected'] = str(error)
                    else: raise AssertionError('ambiguous response accepted')
                else:
                    first = response(reader); buffered = bytes(reader.buffer)
                    second = response(reader)
                    assert first.body == b'hello' and second.body == b'world'
                    assert second.trailers == (('x-lab', 'done'),) and not reader.buffer
                    client.update({'body_hex': [first.body.hex(), second.body.hex()], 'trailers': second.trailers,
                                   'remaining_after_first_hex': buffered.hex(), 'remaining_final_hex': reader.buffer.hex()})
                client.update({'recv_calls': len(reader.pulls), 'recv_hex': [chunk.hex() for chunk in reader.pulls]})
        finally:
            worker.join(timeout=4)
        assert not worker.is_alive() and len(records) == 1 and 'server_error' not in records[0], records
        if bad: assert records[0].get('received_after_response_hex') == '' or 'peer_reset_errno' in records[0]
        print(json.dumps({'verification': 'real-loopback', 'case': 'ambiguous-refused' if bad else 'two-responses-one-connection',
                          'endpoint': listener.getsockname(), 'server': records[0], 'client': client, 'server_thread_joined': True}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    self_check()
    if not args.self_check:
        print(json.dumps({'environment': platform.platform(), 'python': platform.python_version()}))
        network_case(False); network_case(True)
    print(json.dumps({'verification': 'complete', 'sockets_context_closed': True}))


if __name__ == '__main__': main()
