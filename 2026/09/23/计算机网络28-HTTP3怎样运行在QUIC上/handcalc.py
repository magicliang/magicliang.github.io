#!/usr/bin/env python3
"""Finite HTTP/3 mapping checks; this does not open a network socket."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HeaderBlock:
    stream_id: int
    required_insert_count: int


def request_stream_ids(count: int) -> list[int]:
    if count < 0:
        raise ValueError("count must be non-negative")
    return [4 * index for index in range(count)]


def qpack_state(blocks: list[HeaderBlock], insert_count: int) -> dict[str, list[int]]:
    if insert_count < 0:
        raise ValueError("insert_count must be non-negative")
    ready = [block.stream_id for block in blocks if block.required_insert_count <= insert_count]
    blocked = [block.stream_id for block in blocks if block.required_insert_count > insert_count]
    return {"ready": ready, "blocked": blocked}


def protocol_outcome(*, quic_connected: bool, alpn: str | None, allow_fallback: bool) -> str:
    if quic_connected and alpn == "h3":
        return "HTTP/3"
    if allow_fallback:
        return "NEW_TCP_CONNECTION"
    return "FAIL"


def build_result() -> dict[str, object]:
    blocks = [HeaderBlock(0, 3), HeaderBlock(4, 0), HeaderBlock(8, 2)]
    before = qpack_state(blocks, insert_count=2)
    after = qpack_state(blocks, insert_count=3)
    result = {
        "boundary": "finite state arithmetic only; no QUIC or HTTP/3 packets are sent",
        "client_bidirectional_request_streams": request_stream_ids(3),
        "header_blocks": [asdict(block) for block in blocks],
        "qpack_insert_count_2": before,
        "qpack_insert_count_3": after,
        "selection": {
            "h3_selected": protocol_outcome(quic_connected=True, alpn="h3", allow_fallback=True),
            "udp_blocked_with_fallback": protocol_outcome(
                quic_connected=False, alpn=None, allow_fallback=True
            ),
            "udp_blocked_http3_only": protocol_outcome(
                quic_connected=False, alpn=None, allow_fallback=False
            ),
        },
    }
    assert result["client_bidirectional_request_streams"] == [0, 4, 8]
    assert before == {"ready": [4, 8], "blocked": [0]}
    assert after == {"ready": [0, 4, 8], "blocked": []}
    assert result["selection"] == {
        "h3_selected": "HTTP/3",
        "udp_blocked_with_fallback": "NEW_TCP_CONNECTION",
        "udp_blocked_http3_only": "FAIL",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(build_result(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
