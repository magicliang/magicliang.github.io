#!/usr/bin/env python3
"""Compare blocking workers and a selector loop with one framed protocol."""

from __future__ import annotations

import argparse
import json
import selectors
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any

MAX_FRAME = 4096


@dataclass
class FrameState:
    incoming: bytearray = field(default_factory=bytearray)
    outgoing: bytearray = field(default_factory=bytearray)
    expected: int | None = None

    def feed(self, data: bytes) -> list[bytes]:
        self.incoming.extend(data)
        frames: list[bytes] = []
        while True:
            if self.expected is None:
                if len(self.incoming) < 4:
                    break
                self.expected = struct.unpack("!I", self.incoming[:4])[0]
                del self.incoming[:4]
                if self.expected > MAX_FRAME:
                    raise ValueError("frame too large")
            if len(self.incoming) < self.expected:
                break
            frames.append(bytes(self.incoming[: self.expected]))
            del self.incoming[: self.expected]
            self.expected = None
        return frames

    def incomplete(self) -> bool:
        return self.expected is not None or bool(self.incoming)


def encode(payload: bytes) -> bytes:
    return struct.pack("!I", len(payload)) + payload


class BlockingServer:
    def __init__(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.1)
        self.address = self.listener.getsockname()
        self.stop = threading.Event()
        self.events: list[str] = []
        self.lock = threading.Lock()
        self.workers: list[threading.Thread] = []
        self.thread = threading.Thread(target=self._accept_loop, name="blocking-accept")

    def start(self) -> None:
        self.thread.start()

    def _record(self, event: str) -> None:
        with self.lock:
            self.events.append(event)

    def _accept_loop(self) -> None:
        while not self.stop.is_set():
            try:
                conn, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                if self.stop.is_set():
                    return
                raise
            worker = threading.Thread(target=self._serve, args=(conn,), daemon=True)
            self.workers.append(worker)
            worker.start()

    def _serve(self, conn: socket.socket) -> None:
        state = FrameState()
        conn.settimeout(1.0)
        with conn:
            try:
                while True:
                    data = conn.recv(7)
                    if not data:
                        if state.incomplete():
                            self._record("incomplete_eof")
                        return
                    for payload in state.feed(data):
                        conn.sendall(encode(payload.upper()))
                        self._record(f"echo:{payload.decode()}")
            except (ConnectionError, TimeoutError):
                if state.incomplete():
                    self._record("incomplete_eof")

    def close(self) -> None:
        self.stop.set()
        self.listener.close()
        self.thread.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=2)


class SelectorServer:
    def __init__(self) -> None:
        self.selector = selectors.DefaultSelector()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.setblocking(False)
        self.address = self.listener.getsockname()
        self.selector.register(self.listener, selectors.EVENT_READ, None)
        self.states: dict[socket.socket, FrameState] = {}
        self.events: list[str] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="selector-loop")

    def start(self) -> None:
        self.thread.start()

    def _accept_ready(self) -> None:
        while True:
            try:
                conn, _ = self.listener.accept()
            except BlockingIOError:
                return
            conn.setblocking(False)
            state = FrameState()
            self.states[conn] = state
            self.selector.register(conn, selectors.EVENT_READ, state)

    def _close_conn(self, conn: socket.socket, state: FrameState) -> None:
        if state.incomplete():
            self.events.append("incomplete_eof")
        try:
            self.selector.unregister(conn)
        except KeyError:
            pass
        self.states.pop(conn, None)
        conn.close()

    def _service(self, conn: socket.socket, state: FrameState, mask: int) -> None:
        if mask & selectors.EVENT_READ:
            try:
                data = conn.recv(7)
            except BlockingIOError:
                data = None
            except ConnectionError:
                data = b""
            if data == b"":
                self._close_conn(conn, state)
                return
            if data:
                for payload in state.feed(data):
                    state.outgoing.extend(encode(payload.upper()))
                    self.events.append(f"echo:{payload.decode()}")
        if mask & selectors.EVENT_WRITE and state.outgoing:
            try:
                sent = conn.send(state.outgoing)
            except BlockingIOError:
                sent = 0
            del state.outgoing[:sent]
        wanted = selectors.EVENT_READ
        if state.outgoing:
            wanted |= selectors.EVENT_WRITE
        if conn in self.states:
            self.selector.modify(conn, wanted, state)

    def _loop(self) -> None:
        while not self.stop.is_set():
            for key, mask in self.selector.select(timeout=0.05):
                if key.fileobj is self.listener:
                    self._accept_ready()
                else:
                    self._service(key.fileobj, key.data, mask)

    def close(self) -> None:
        self.stop.set()
        self.thread.join(timeout=2)
        for conn, state in list(self.states.items()):
            self._close_conn(conn, state)
        self.selector.unregister(self.listener)
        self.listener.close()
        self.selector.close()


def recv_frame(conn: socket.socket) -> bytes:
    data = bytearray()
    expected: int | None = None
    while expected is None or len(data) < expected:
        chunk = conn.recv(3)
        if not chunk:
            raise EOFError("response ended early")
        data.extend(chunk)
        if expected is None and len(data) >= 4:
            expected = 4 + struct.unpack("!I", data[:4])[0]
    return bytes(data[4:expected])


def exchange(address: tuple[str, int], payload: bytes, chunks: list[int] | None = None) -> bytes:
    wire = encode(payload)
    with socket.create_connection(address, timeout=2) as conn:
        conn.settimeout(2)
        if chunks is None:
            conn.sendall(wire)
        else:
            position = 0
            for size in chunks:
                conn.sendall(wire[position : position + size])
                position += size
            conn.sendall(wire[position:])
        return recv_frame(conn)


def run_mode(mode: str) -> dict[str, Any]:
    server: BlockingServer | SelectorServer
    server = BlockingServer() if mode == "blocking-workers" else SelectorServer()
    server.start()
    slow_ready = threading.Event()
    release_slow = threading.Event()
    slow_result: list[bytes] = []

    def slow_client() -> None:
        wire = encode(b"slow")
        with socket.create_connection(server.address, timeout=2) as conn:
            conn.settimeout(2)
            conn.sendall(wire[:4])
            slow_ready.set()
            if not release_slow.wait(timeout=2):
                raise TimeoutError("slow client was not released")
            conn.sendall(wire[4:])
            slow_result.append(recv_frame(conn))

    slow_thread = threading.Thread(target=slow_client, name=f"{mode}-slow")
    try:
        slow_thread.start()
        if not slow_ready.wait(timeout=2):
            raise TimeoutError("slow client did not send its header")
        fast_result = exchange(server.address, b"fast")
        fragmented_result = exchange(server.address, b"fragmented", [1, 1, 2, 3])
        with socket.create_connection(server.address, timeout=2) as abrupt:
            abrupt.sendall(struct.pack("!I", 5) + b"xy")
        deadline = time.monotonic() + 2
        while "incomplete_eof" not in server.events and time.monotonic() < deadline:
            time.sleep(0.01)
        release_slow.set()
        slow_thread.join(timeout=2)
        result = {
            "mode": mode,
            "selector": type(server.selector).__name__ if isinstance(server, SelectorServer) else None,
            "fast_while_slow_incomplete": fast_result.decode(),
            "fragmented_request": fragmented_result.decode(),
            "slow_request": slow_result[0].decode(),
            "incomplete_eof_recorded": "incomplete_eof" in server.events,
            "active_connection_units": len(server.workers) if isinstance(server, BlockingServer) else 1,
        }
        assert result["fast_while_slow_incomplete"] == "FAST"
        assert result["fragmented_request"] == "FRAGMENTED"
        assert result["slow_request"] == "SLOW"
        assert result["incomplete_eof_recorded"] is True
        return result
    finally:
        release_slow.set()
        slow_thread.join(timeout=2)
        server.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = {
        "boundary": "loopback correctness only; connection-unit counts are not throughput",
        "runs": [run_mode("blocking-workers"), run_mode("selector-loop")],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
