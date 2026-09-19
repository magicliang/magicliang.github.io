#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Log an owned loopback exchange; optionally pause for a separate capture."""
import argparse
import json
import platform
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / '2026-09-19-计算机网络02-socket读写与消息边界'))
from framing import Decoder, encode


def record(event: str, **fields: str | int | tuple[str, int] | list[tuple[int, ...]]) -> None:
    print(json.dumps({'event': event, 'monotonic_ns': time.monotonic_ns(),
                      'wall_ns': time.time_ns(), **fields}, ensure_ascii=False), flush=True)


def read_frame(sock: socket.socket) -> bytes:
    decoder = Decoder()
    while True:
        block = sock.recv(5)
        if not block:
            decoder.finish()
            raise EOFError('connection ended before message')
        record('recv_return', fd=sock.fileno(), hex=block.hex())
        messages = decoder.feed(block)
        if messages:
            assert len(messages) == 1
            return messages[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-for-capture', action='store_true',
                        help='print the owned port and wait for Enter before connecting')
    args = parser.parse_args()
    record('environment', python=platform.python_version(), system=platform.platform())
    model = [(1000, 0, 1, 0, 1001), (1001, 14, 0, 0, 1015),
             (1015, 0, 0, 0, 1015), (1015, 0, 0, 1, 1016)]
    for seq, length, syn, fin, expected in model:
        assert (seq + length + syn + fin) % (2**32) == expected
    assert ((2**32 - 2) + 4) % (2**32) == 2
    record('hand_calculation_passed', scope='invented sequence numbers; not captured packets', rows=model)
    with socket.socket() as listener, socket.socket() as client:
        listener.settimeout(5)
        client.settimeout(5)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        address = listener.getsockname()
        record('listener_ready', address=address)
        if args.wait_for_capture:
            input('Start capture on this port, then press Enter: ')
        record('connect_call')
        client.connect(address)
        record('connect_return', local=client.getsockname(), peer=client.getpeername())
        connection, peer = listener.accept()
        with connection:
            connection.settimeout(5)
            record('accept_return', peer=peer)
            payload = b'network-03'
            wire = encode(payload)
            client.sendall(wire)
            record('sendall_return', wire_hex=wire.hex(), application_read_started=False)
            assert read_frame(connection) == payload
            record('server_message_decoded', payload_hex=payload.hex())
            connection.sendall(wire)
            record('server_reply_submitted')
            assert read_frame(client) == payload
            record('client_reply_verified', bytes=len(payload))
    record('local_exchange_complete', packet_capture_verified=False)


if __name__ == '__main__':
    main()
