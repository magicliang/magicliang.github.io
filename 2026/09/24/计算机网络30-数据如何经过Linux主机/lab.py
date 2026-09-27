#!/usr/bin/env python3
"""Align application events with Linux TCP and host-wide counters on loopback."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import socket
import sys
import threading
import time
from pathlib import Path


PAYLOAD = bytes(range(256)) * 256
TCP_STATES = {"01": "ESTABLISHED", "0A": "LISTEN"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a loopback TCP exchange and align it with /proc snapshots."
    )
    parser.add_argument(
        "--queue-wait",
        type=float,
        default=2.0,
        help="seconds to wait for a non-zero server receive queue (default: 2.0)",
    )
    return parser.parse_args()


def decode_ipv4_endpoint(value: str) -> tuple[str, int]:
    address_hex, port_hex = value.split(":")
    address = socket.inet_ntoa(bytes.fromhex(address_hex)[::-1])
    return address, int(port_hex, 16)


def tcp_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    lines = Path("/proc/net/tcp").read_text(encoding="ascii").splitlines()[1:]
    for line in lines:
        fields = line.split()
        tx_hex, rx_hex = fields[4].split(":")
        rows.append(
            {
                "local": decode_ipv4_endpoint(fields[1]),
                "remote": decode_ipv4_endpoint(fields[2]),
                "state": TCP_STATES.get(fields[3], fields[3]),
                "tx_queue": int(tx_hex, 16),
                "rx_queue": int(rx_hex, 16),
            }
        )
    return rows


def find_tcp(local: tuple[str, int], remote: tuple[str, int]) -> dict[str, object] | None:
    for row in tcp_rows():
        if tuple(row["local"]) == local and tuple(row["remote"]) == remote:
            return row
    return None


def netdev(interface: str) -> dict[str, int]:
    for line in Path("/proc/net/dev").read_text(encoding="ascii").splitlines()[2:]:
        name, values = line.split(":", 1)
        if name.strip() != interface:
            continue
        fields = [int(value) for value in values.split()]
        return {
            "rx_bytes": fields[0],
            "rx_packets": fields[1],
            "tx_bytes": fields[8],
            "tx_packets": fields[9],
        }
    raise RuntimeError(f"interface not found: {interface}")


def tcp_snmp() -> dict[str, int]:
    lines = Path("/proc/net/snmp").read_text(encoding="ascii").splitlines()
    for index in range(len(lines) - 1):
        if lines[index].startswith("Tcp:") and lines[index + 1].startswith("Tcp:"):
            names = lines[index].split()[1:]
            values = [int(value) for value in lines[index + 1].split()[1:]]
            data = dict(zip(names, values))
            return {name: data[name] for name in ("ActiveOpens", "PassiveOpens", "InSegs", "OutSegs", "RetransSegs")}
    raise RuntimeError("Tcp section not found in /proc/net/snmp")


def softnet_summary() -> dict[str, object]:
    rows = Path("/proc/net/softnet_stat").read_text(encoding="ascii").splitlines()
    parsed = [[int(value, 16) for value in row.split()[:3]] for row in rows]
    return {
        "cpu_rows": len(parsed),
        "first_three_columns_sum": [sum(row[index] for row in parsed) for index in range(3)],
    }


def delta(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {key: after[key] - before[key] for key in before}


def endpoint(value: tuple[str, int]) -> dict[str, object]:
    return {"address": value[0], "port": value[1]}


def main() -> int:
    args = parse_args()
    before_dev = netdev("lo")
    before_snmp = tcp_snmp()
    before_softnet = softnet_summary()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    accepted = threading.Event()
    allow_receive = threading.Event()
    receive_done = threading.Event()
    allow_close = threading.Event()
    server_result: dict[str, object] = {}

    def serve() -> None:
        conn, _ = listener.accept()
        try:
            server_result["local"] = conn.getsockname()
            server_result["remote"] = conn.getpeername()
            accepted.set()
            if not allow_receive.wait(5):
                raise TimeoutError("receive gate timed out")
            digest = hashlib.sha256()
            received = 0
            while received < len(PAYLOAD):
                chunk = conn.recv(min(16384, len(PAYLOAD) - received))
                if not chunk:
                    break
                digest.update(chunk)
                received += len(chunk)
            server_result["received_bytes"] = received
            server_result["sha256"] = digest.hexdigest()
            conn.sendall(b"APP_OK\n")
            receive_done.set()
            if not allow_close.wait(5):
                raise TimeoutError("close gate timed out")
        except BaseException as error:  # surfaced in the main thread
            server_result["error"] = repr(error)
            receive_done.set()
        finally:
            conn.close()

    thread = threading.Thread(target=serve, name="loopback-server")
    thread.start()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(listener.getsockname())
    if not accepted.wait(5):
        raise TimeoutError("accept timed out")

    client_local = client.getsockname()
    client_remote = client.getpeername()
    server_local = tuple(server_result["local"])
    server_remote = tuple(server_result["remote"])
    client.sendall(PAYLOAD)
    sendall_returned = True

    deadline = time.monotonic() + args.queue_wait
    before_receive_client = None
    before_receive_server = None
    while time.monotonic() < deadline:
        before_receive_client = find_tcp(client_local, client_remote)
        before_receive_server = find_tcp(server_local, server_remote)
        if before_receive_server and int(before_receive_server["rx_queue"]) > 0:
            break
        time.sleep(0.01)

    allow_receive.set()
    response = client.recv(64)
    if not receive_done.wait(5):
        raise TimeoutError("server receive timed out")
    after_receive_client = find_tcp(client_local, client_remote)
    after_receive_server = find_tcp(server_local, server_remote)

    allow_close.set()
    client.close()
    listener.close()
    thread.join(5)
    if thread.is_alive():
        raise RuntimeError("server thread did not stop")

    after_dev = netdev("lo")
    after_snmp = tcp_snmp()
    after_softnet = softnet_summary()
    expected_hash = hashlib.sha256(PAYLOAD).hexdigest()
    assertions = {
        "sendall_returned": sendall_returned,
        "both_established_rows_found_before_receive": bool(
            before_receive_client
            and before_receive_server
            and before_receive_client["state"] == "ESTABLISHED"
            and before_receive_server["state"] == "ESTABLISHED"
        ),
        "server_rx_queue_nonzero_before_application_recv": bool(
            before_receive_server and int(before_receive_server["rx_queue"]) > 0
        ),
        "server_received_exact_payload": server_result.get("received_bytes") == len(PAYLOAD),
        "server_payload_hash_matches": server_result.get("sha256") == expected_hash,
        "application_response_received": response == b"APP_OK\n",
        "loopback_counters_increased": (
            after_dev["rx_bytes"] > before_dev["rx_bytes"]
            and after_dev["tx_bytes"] > before_dev["tx_bytes"]
        ),
    }

    report = {
        "environment": {
            "python": platform.python_version(),
            "kernel": platform.release(),
            "platform": platform.system(),
        },
        "application": {
            "payload_bytes": len(PAYLOAD),
            "payload_sha256": expected_hash,
            "client_local": endpoint(client_local),
            "client_remote": endpoint(client_remote),
            "server_local": endpoint(server_local),
            "server_remote": endpoint(server_remote),
            "server_received_bytes": server_result.get("received_bytes"),
            "server_received_sha256": server_result.get("sha256"),
            "response": response.decode("ascii").strip(),
            "server_error": server_result.get("error"),
        },
        "proc_net_tcp": {
            "before_server_recv": {
                "client": before_receive_client,
                "server": before_receive_server,
            },
            "after_server_recv": {
                "client": after_receive_client,
                "server": after_receive_server,
            },
        },
        "shared_host_counters": {
            "loopback_before": before_dev,
            "loopback_after": after_dev,
            "loopback_delta": delta(after_dev, before_dev),
            "tcp_snmp_before": before_snmp,
            "tcp_snmp_after": after_snmp,
            "tcp_snmp_delta": delta(after_snmp, before_snmp),
            "softnet_before": before_softnet,
            "softnet_after": after_softnet,
        },
        "assertions": assertions,
        "boundaries": [
            "all traffic is self-owned IPv4 loopback traffic",
            "host counters are shared and cannot be uniquely attributed to this process",
            "loopback does not validate physical NIC interrupts, rings, offloads, frames, or performance",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(assertions.values()) and server_result.get("error") is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
