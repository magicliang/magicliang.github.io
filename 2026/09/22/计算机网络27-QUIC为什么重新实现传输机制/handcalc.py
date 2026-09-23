#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def packet_space_example() -> dict:
    sent = {
        "initial": [0, 1],
        "handshake": [0],
        "application": [0, 1, 3],
    }
    frames = [
        {"space": "application", "packet": 0, "stream": 0, "offset": 0, "length": 6},
        {"space": "application", "packet": 1, "stream": 4, "offset": 0, "length": 5},
        {"space": "application", "packet": 3, "stream": 0, "offset": 6, "length": 4},
    ]
    assert sent["initial"][0] == sent["handshake"][0] == sent["application"][0]
    assert sent["application"] == [0, 1, 3]
    assert sum(f["length"] for f in frames if f["stream"] == 0) == 10
    return {"packet_numbers": sent, "stream_bytes": {0: 10, 4: 5}}


def stream_gap_example() -> dict:
    received = {
        0: [(0, 6), (10, 4)],
        4: [(0, 5)],
    }
    deliverable = {}
    gaps = {}
    for stream_id, ranges in received.items():
        cursor = 0
        stream_gaps = []
        for offset, length in sorted(ranges):
            if offset > cursor:
                stream_gaps.append((cursor, offset))
                break
            cursor = max(cursor, offset + length)
        deliverable[stream_id] = cursor
        gaps[stream_id] = stream_gaps
    cwnd = 12000
    inflight = 9000
    retransmit_need = 3500
    allowed = max(0, cwnd - inflight)
    assert deliverable == {0: 6, 4: 5}
    assert gaps[0] == [(6, 10)]
    assert gaps[4] == []
    assert allowed == 3000 < retransmit_need
    return {"deliverable_offsets": deliverable, "gaps": gaps, "shared_congestion_credit": allowed}


def pto_example() -> dict:
    smoothed_rtt = 40
    rttvar = 8
    granularity = 1
    max_ack_delay = 25
    pto = smoothed_rtt + max(4 * rttvar, granularity) + max_ack_delay
    assert pto == 97
    return {
        "formula": "smoothed_rtt + max(4*rttvar, kGranularity) + max_ack_delay",
        "inputs_ms": {
            "smoothed_rtt": smoothed_rtt,
            "rttvar": rttvar,
            "kGranularity": granularity,
            "max_ack_delay": max_ack_delay,
        },
        "pto_ms": pto,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check finite QUIC packet-space, stream, congestion, and PTO examples."
    )
    parser.parse_args()
    result = {
        "packet_space_example": packet_space_example(),
        "stream_gap_example": stream_gap_example(),
        "pto_example": pto_example(),
        "boundary": "finite arithmetic only; not a QUIC implementation or network experiment",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
