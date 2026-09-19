#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 experiment.py
"""Deterministic decoder cases plus one real loopback framed exchange."""
from __future__ import annotations

import json
import platform
import socket
from concurrent.futures import ThreadPoolExecutor

from framing import Decoder, FrameTooLarge, MAX_FRAME, TruncatedFrame, encode


def decoder_checks() -> None:
    wanted = [b"alpha", "网".encode(), b"", b"omega"]
    wire = b"".join(map(encode, wanted))
    for width in (1, 2, 3, 4, 5, 7, len(wire)):
        decoder = Decoder()
        actual: list[bytes] = []
        for start in range(0, len(wire), width):
            actual.extend(decoder.feed(wire[start:start + width]))
        decoder.finish()
        assert actual == wanted
        print(json.dumps({"test": "fixed_chunks", "width": width, "messages": len(actual)}))
    for cut in (1, 3, 4, 6):
        decoder = Decoder()
        decoder.feed(encode(b"alpha")[:cut])
        try:
            decoder.finish()
        except TruncatedFrame:
            print(json.dumps({"test": "truncated_eof_rejected", "cut": cut}))
        else:
            raise AssertionError("truncation accepted")
    decoder = Decoder()
    try:
        decoder.feed((MAX_FRAME + 1).to_bytes(4, "big"))
    except FrameTooLarge:
        print(json.dumps({"test": "oversize_header_rejected", "length": MAX_FRAME + 1}))
    else:
        raise AssertionError("oversize accepted")
    decoder = Decoder()
    assert decoder.feed(encode(b"x") + encode(b"yz")[:2]) == [b"x"]
    assert decoder.feed(encode(b"yz")[2:]) == [b"yz"]
    decoder.finish()
    print(json.dumps({"test": "complete_plus_partial_next", "pass": True}))


def receive_messages(stream: socket.socket, read_size: int) -> list[bytes]:
    decoder = Decoder()
    messages: list[bytes] = []
    while True:
        chunk = stream.recv(read_size)
        if not chunk:
            decoder.finish()
            return messages
        messages.extend(decoder.feed(chunk))


def loopback() -> None:
    wanted = [b"one", "网".encode(), b"", b"x" * MAX_FRAME]
    wire = b"".join(map(encode, wanted))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(5)

        def serve() -> None:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(5)
                messages = receive_messages(connection, 7)
                assert messages == wanted
                for message in messages:
                    connection.sendall(encode(message))
                connection.shutdown(socket.SHUT_WR)

        with ThreadPoolExecutor(max_workers=1) as pool:
            worker = pool.submit(serve)
            with socket.create_connection(listener.getsockname(), timeout=5) as client:
                for offset in range(0, len(wire), 3):
                    client.sendall(wire[offset:offset + 3])
                client.shutdown(socket.SHUT_WR)
                assert receive_messages(client, 5) == wanted
            worker.result(timeout=5)
    print(json.dumps({"test": "loopback_echo", "messages": len(wanted),
                      "payload_bytes": sum(map(len, wanted)), "pass": True}))


def main() -> None:
    print(json.dumps({"python": platform.python_version(), "system": platform.system(),
                      "release": platform.release(), "machine": platform.machine()}))
    decoder_checks()
    loopback()


if __name__ == "__main__":
    main()
