#!/usr/bin/env python3
"""Loopback demonstration of per-connection backend selection."""

from __future__ import annotations

import argparse
import json
import socket
import socketserver
import threading
import time


class BackendHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        while True:
            line = self.rfile.readline()
            if not line:
                return
            self.wfile.write(self.server.backend_name.encode() + b":" + line)
            self.wfile.flush()


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False


class Backend:
    def __init__(self, name: str) -> None:
        self.server = ThreadingServer(("127.0.0.1", 0), BackendHandler)
        self.server.backend_name = name
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def address(self) -> tuple[str, int]:
        return self.server.server_address

    def start(self) -> None:
        self.thread.start()

    def stop_listening(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)


class ProxyHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        upstream_name, upstream_address = self.server.choose_backend()
        with socket.create_connection(upstream_address, timeout=2) as upstream:
            upstream_file = upstream.makefile("rwb")
            while True:
                line = self.rfile.readline()
                if not line:
                    return
                upstream_file.write(line)
                upstream_file.flush()
                response = upstream_file.readline()
                if not response:
                    return
                self.wfile.write(response)
                self.wfile.flush()


class Proxy(ThreadingServer):
    def __init__(self, backends: dict[str, tuple[str, int]]) -> None:
        super().__init__(("127.0.0.1", 0), ProxyHandler)
        self.backends = backends
        self.healthy = set(backends)
        self.lock = threading.Lock()

    def choose_backend(self) -> tuple[str, tuple[str, int]]:
        with self.lock:
            for name in self.backends:
                if name in self.healthy:
                    return name, self.backends[name]
        raise RuntimeError("no healthy backend")

    def set_health(self, health: dict[str, bool]) -> None:
        with self.lock:
            self.healthy = {name for name, ok in health.items() if ok}


def check(address: tuple[str, int]) -> bool:
    try:
        with socket.create_connection(address, timeout=0.3):
            return True
    except OSError:
        return False


def exchange(file, message: str) -> str:
    file.write(message.encode() + b"\n")
    file.flush()
    return file.readline().decode().strip()


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Show existing and new connections after a backend listener closes.").parse_args()


def main() -> int:
    parse_args()
    backend_a, backend_b = Backend("A"), Backend("B")
    backend_a.start()
    backend_b.start()
    proxy = Proxy({"A": backend_a.address, "B": backend_b.address})
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()

    existing_socket = socket.create_connection(proxy.server_address, timeout=2)
    existing = existing_socket.makefile("rwb")
    first = exchange(existing, "first")

    backend_a.stop_listening()
    time.sleep(0.05)
    health = {"A": check(backend_a.address), "B": check(backend_b.address)}
    proxy.set_health(health)

    existing_after = exchange(existing, "after-listener-close")
    with socket.create_connection(proxy.server_address, timeout=2) as new_socket:
        new = new_socket.makefile("rwb")
        new_after = exchange(new, "new-connection")

    existing.close()
    existing_socket.close()
    proxy.shutdown()
    proxy.server_close()
    proxy_thread.join(2)
    backend_b.stop_listening()

    assertions = {
        "existing_connection_initially_uses_a": first == "A:first",
        "health_check_marks_a_down": health == {"A": False, "B": True},
        "existing_connection_stays_on_a": existing_after == "A:after-listener-close",
        "new_connection_uses_b": new_after == "B:new-connection",
    }
    report = {
        "events": {
            "existing_before": first,
            "health_after_a_listener_close": health,
            "existing_after": existing_after,
            "new_after": new_after,
        },
        "assertions": assertions,
        "boundaries": [
            "loopback teaching proxy with per-connection selection",
            "not HTTP, TLS, production load balancing, draining, retry, or a performance test",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
