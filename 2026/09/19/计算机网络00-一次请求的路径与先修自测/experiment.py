#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 experiment.py --case all
"""Observe three local TCP scenarios, without modifying network configuration."""
from __future__ import annotations

import argparse
import json
import platform
import socket
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Final

PAYLOAD: Final = b"network-00"
TIMEOUT: Final = 5.0


def emit(event: str, detail: str = "") -> None:
    print(json.dumps({"t_ns": time.monotonic_ns(), "event": event,
                      "detail": detail}, ensure_ascii=False), flush=True)


def read_exact(stream: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        part = stream.recv(size - len(data))
        if not part:
            raise EOFError(f"received {len(data)} of {size} bytes")
        data.extend(part)
    return bytes(data)


def refused() -> None:
    # Keep the port reserved but deliberately never call listen().
    with socket.socket() as reserved, socket.socket() as client:
        reserved.bind(("127.0.0.1", 0))
        client.settimeout(TIMEOUT)
        emit("refused.connect_begin")
        try:
            client.connect(reserved.getsockname())
        except ConnectionRefusedError as exc:
            emit("refused.connect_error", type(exc).__name__)
        except TimeoutError:
            emit("refused.environment_gap", "timeout instead of connection refusal")
        else:
            raise AssertionError("non-listening local port accepted connection")


def exchange(paused: bool) -> None:
    scenario = "paused" if paused else "echo"
    read_allowed = threading.Event()
    accepted = threading.Event()
    app_read = threading.Event()
    if not paused:
        read_allowed.set()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(TIMEOUT)

        def serve() -> None:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(TIMEOUT)
                emit(scenario + ".server_accepted")
                accepted.set()
                if not read_allowed.wait(TIMEOUT):
                    raise TimeoutError("test coordinator did not release reader")
                data = read_exact(connection, len(PAYLOAD))
                emit(scenario + ".server_read", data.hex())
                app_read.set()
                connection.sendall(data)
                emit(scenario + ".server_reply_returned")

        with ThreadPoolExecutor(max_workers=1) as pool:
            server = pool.submit(serve)
            try:
                with socket.socket() as client:
                    client.settimeout(TIMEOUT)
                    emit(scenario + ".connect_begin")
                    client.connect(listener.getsockname())
                    emit(scenario + ".connect_returned")
                    if not accepted.wait(TIMEOUT):
                        raise TimeoutError("server did not accept")
                    client.sendall(PAYLOAD)
                    emit(scenario + ".sendall_returned", str(len(PAYLOAD)))
                    if paused:
                        assert not app_read.is_set()
                        emit("paused.reader_still_gated")
                        read_allowed.set()
                    reply = read_exact(client, len(PAYLOAD))
                    assert reply == PAYLOAD
                    emit(scenario + ".reply_verified", reply.hex())
            finally:
                read_allowed.set()
            server.result(timeout=TIMEOUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("all", "refused", "paused", "echo"),
                        default="all")
    args = parser.parse_args()
    emit("environment", f"Python {platform.python_version()}; "
         f"{platform.system()} {platform.release()} {platform.machine()}")
    encoded = struct.pack("!I", 258)
    assert encoded == bytes.fromhex("00000102")
    assert struct.unpack("!I", encoded)[0] == 258
    emit("prerequisite", "258 -> 00000102; 1 byte = 8 bits")
    if args.case in ("all", "refused"):
        refused()
    if args.case in ("all", "paused"):
        exchange(True)
    if args.case in ("all", "echo"):
        exchange(False)
    emit("scenarios_completed", args.case)


if __name__ == "__main__":
    main()
