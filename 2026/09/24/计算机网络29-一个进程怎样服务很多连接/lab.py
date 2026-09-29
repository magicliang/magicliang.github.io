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
MAX_OUTGOING = MAX_FRAME + 4
CONNECTION_DEADLINE_SECONDS = 2.0


@dataclass
class FrameState:
    incoming: bytearray = field(default_factory=bytearray)
    outgoing: bytearray = field(default_factory=bytearray)
    expected: int | None = None
    read_eof: bool = False
    deadline: float | None = None

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
            except ValueError as exc:
                self._record(f"protocol_error:{exc}")
            except TimeoutError:
                self._record("connection_timeout")
            except ConnectionError as exc:
                self._record(f"connection_error:{type(exc).__name__}")

    def close(self) -> None:
        self.stop.set()
        self.listener.close()
        self.thread.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=2)


class SelectorServer:
    def __init__(self, connection_deadline: float = CONNECTION_DEADLINE_SECONDS) -> None:
        self.selector = selectors.DefaultSelector()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.setblocking(False)
        self.address = self.listener.getsockname()
        self.selector.register(self.listener, selectors.EVENT_READ, None)
        self.states: dict[socket.socket, FrameState] = {}
        self.events: list[str] = []
        self.connection_deadline = connection_deadline
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
            state = FrameState(deadline=time.monotonic() + self.connection_deadline)
            self.states[conn] = state
            self.selector.register(conn, selectors.EVENT_READ, state)

    def _close_conn(self, conn: socket.socket, state: FrameState, reason: str) -> None:
        self.events.append(reason)
        try:
            self.selector.unregister(conn)
        except (OSError, KeyError, ValueError):
            pass
        self.states.pop(conn, None)
        try:
            conn.close()
        except OSError:
            pass

    @staticmethod
    def _queue_response(state: FrameState, payload: bytes) -> None:
        response = encode(payload.upper())
        if len(state.outgoing) + len(response) > MAX_OUTGOING:
            raise BufferError("outgoing buffer limit exceeded")
        state.outgoing.extend(response)

    def _send(self, conn: socket.socket, data: bytearray) -> int:
        return conn.send(data)

    def _service(self, conn: socket.socket, state: FrameState, mask: int) -> None:
        if mask & selectors.EVENT_READ:
            try:
                data = conn.recv(7)
            except BlockingIOError:
                data = None
            except OSError as exc:
                self._close_conn(conn, state, f"read_error:{type(exc).__name__}")
                return
            if data == b"":
                state.read_eof = True
                if state.incomplete():
                    self._close_conn(conn, state, "incomplete_eof")
                    return
            if data:
                try:
                    for payload in state.feed(data):
                        self._queue_response(state, payload)
                        rendered = payload.decode("utf-8", errors="backslashreplace")
                        self.events.append(f"echo:{rendered}")
                except (ValueError, BufferError) as exc:
                    self._close_conn(conn, state, f"protocol_error:{exc}")
                    return
        if mask & selectors.EVENT_WRITE and state.outgoing:
            try:
                sent = self._send(conn, state.outgoing)
            except BlockingIOError:
                sent = None
            except OSError as exc:
                self._close_conn(conn, state, f"write_error:{type(exc).__name__}")
                return
            if sent is None:
                return
            if sent == 0:
                self._close_conn(conn, state, "write_error:zero_send")
                return
            del state.outgoing[:sent]
        if state.read_eof and not state.outgoing:
            self._close_conn(conn, state, "response_drained_after_eof")
            return
        wanted = 0 if state.read_eof else selectors.EVENT_READ
        if state.outgoing:
            wanted |= selectors.EVENT_WRITE
        if conn in self.states:
            try:
                self.selector.modify(conn, wanted, state)
            except (OSError, KeyError, ValueError) as exc:
                self._close_conn(conn, state, f"selector_error:{type(exc).__name__}")

    def _expire_connections(self) -> None:
        now = time.monotonic()
        for conn, state in list(self.states.items()):
            if state.deadline is not None and now >= state.deadline:
                self._close_conn(conn, state, "connection_deadline")

    def _loop(self) -> None:
        while not self.stop.is_set():
            for key, mask in self.selector.select(timeout=0.05):
                if key.fileobj is self.listener:
                    self._accept_ready()
                else:
                    self._service(key.fileobj, key.data, mask)
            self._expire_connections()

    def close(self) -> None:
        self.stop.set()
        self.thread.join(timeout=2)
        for conn, state in list(self.states.items()):
            self._close_conn(conn, state, "server_shutdown")
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


def exchange_after_write_shutdown(address: tuple[str, int], payload: bytes) -> bytes:
    with socket.create_connection(address, timeout=2) as conn:
        conn.settimeout(2)
        conn.sendall(encode(payload))
        conn.shutdown(socket.SHUT_WR)
        return recv_frame(conn)


def wait_for_event(events: list[str], prefix: str, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(event.startswith(prefix) for event in events):
            return True
        time.sleep(0.01)
    return False


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
        half_close_result = exchange_after_write_shutdown(server.address, b"half-close")
        with socket.create_connection(server.address, timeout=2) as abrupt:
            abrupt.sendall(struct.pack("!I", 5) + b"xy")
        incomplete_eof_recorded = wait_for_event(server.events, "incomplete_eof")
        with socket.create_connection(server.address, timeout=2) as oversized:
            oversized.sendall(struct.pack("!I", MAX_FRAME + 1))
        oversized_rejected = wait_for_event(server.events, "protocol_error:frame too large")
        normal_after_oversized = exchange(server.address, b"after-error")
        release_slow.set()
        slow_thread.join(timeout=2)
        result = {
            "mode": mode,
            "selector": type(server.selector).__name__ if isinstance(server, SelectorServer) else None,
            "fast_while_slow_incomplete": fast_result.decode(),
            "fragmented_request": fragmented_result.decode(),
            "half_close_response": half_close_result.decode(),
            "slow_request": slow_result[0].decode(),
            "incomplete_eof_recorded": incomplete_eof_recorded,
            "oversized_frame_isolated": oversized_rejected,
            "normal_after_oversized": normal_after_oversized.decode(),
            "active_connection_units": len(server.workers) if isinstance(server, BlockingServer) else 1,
        }
        assert result["fast_while_slow_incomplete"] == "FAST"
        assert result["fragmented_request"] == "FRAGMENTED"
        assert result["half_close_response"] == "HALF-CLOSE"
        assert result["slow_request"] == "SLOW"
        assert result["incomplete_eof_recorded"] is True
        assert result["oversized_frame_isolated"] is True
        assert result["normal_after_oversized"] == "AFTER-ERROR"
        return result
    finally:
        release_slow.set()
        slow_thread.join(timeout=2)
        server.close()


class WriteFaultSelectorServer(SelectorServer):
    """Inject one write-side connection failure without changing loop control."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_next_write = True

    def _send(self, conn: socket.socket, data: bytearray) -> int:
        if self.fail_next_write:
            self.fail_next_write = False
            raise BrokenPipeError("synthetic write failure")
        return super()._send(conn, data)


def run_selector_controls() -> dict[str, Any]:
    write_server = WriteFaultSelectorServer()
    write_server.start()
    try:
        with socket.create_connection(write_server.address, timeout=2) as conn:
            conn.sendall(encode(b"write-fault"))
            conn.shutdown(socket.SHUT_WR)
            try:
                recv_frame(conn)
            except (ConnectionError, EOFError):
                pass
        write_error_isolated = wait_for_event(write_server.events, "write_error:")
        normal_after_write_error = exchange(write_server.address, b"still-running")
    finally:
        write_server.close()

    deadline_server = SelectorServer(connection_deadline=0.05)
    deadline_server.start()
    try:
        with socket.create_connection(deadline_server.address, timeout=2) as conn:
            conn.sendall(struct.pack("!I", 4))
            deadline_enforced = wait_for_event(deadline_server.events, "connection_deadline")
        normal_after_deadline = exchange(deadline_server.address, b"deadline-ok")
    finally:
        deadline_server.close()

    bounded_state = FrameState()
    bounded_state.outgoing.extend(b"x" * MAX_OUTGOING)
    try:
        SelectorServer._queue_response(bounded_state, b"x")
    except BufferError:
        outgoing_limit_enforced = True
    else:
        outgoing_limit_enforced = False

    result = {
        "write_error_isolated": write_error_isolated,
        "normal_after_write_error": normal_after_write_error.decode(),
        "connection_deadline_enforced": deadline_enforced,
        "normal_after_deadline": normal_after_deadline.decode(),
        "outgoing_limit_bytes": MAX_OUTGOING,
        "outgoing_limit_enforced": outgoing_limit_enforced,
    }
    assert result["write_error_isolated"] is True
    assert result["normal_after_write_error"] == "STILL-RUNNING"
    assert result["connection_deadline_enforced"] is True
    assert result["normal_after_deadline"] == "DEADLINE-OK"
    assert result["outgoing_limit_enforced"] is True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = {
        "boundary": "loopback correctness only; connection-unit counts are not throughput",
        "runs": [run_mode("blocking-workers"), run_mode("selector-loop")],
        "selector_controls": run_selector_controls(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
