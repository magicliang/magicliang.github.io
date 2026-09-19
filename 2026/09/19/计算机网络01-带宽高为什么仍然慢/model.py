#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 model.py
"""Check exact arithmetic for a specified store-and-forward queue model."""
from __future__ import annotations

import json
from fractions import Fraction


def main() -> None:
    bits = 1500 * 8
    rate = 10_000_000
    propagation = Fraction(2, 1000)
    serialization = Fraction(bits, rate)
    first_packet = 3 * (serialization + propagation)
    pipelined_ten = 3 * propagation + (3 + 10 - 1) * serialization
    assert serialization == Fraction(12, 10_000)
    assert first_packet == Fraction(96, 10_000)
    assert pipelined_ten == Fraction(204, 10_000)
    finish = Fraction(0)
    waits: list[Fraction] = []
    for index in range(10):
        arrival = Fraction(index, 1000)
        start = max(arrival, finish)
        waits.append(start - arrival)
        finish = start + serialization
    assert waits == [Fraction(i, 5000) for i in range(10)]
    bdp_bytes = Fraction(rate, 8) * Fraction(40, 1000)
    window_bound = Fraction(10_000 * 8, 1) / Fraction(40, 1000)
    assert bdp_bytes == 50_000
    assert window_bound == 2_000_000
    print(json.dumps({
        "evidence_type": "exact_arithmetic_model_not_network_measurement",
        "packet_bits": bits, "rate_bits_per_second": rate,
        "serialization_ms": str(serialization * 1000),
        "three_link_first_packet_ms": str(first_packet * 1000),
        "three_link_ten_packets_ms": str(pipelined_ten * 1000),
        "queue_wait_ms": [str(v * 1000) for v in waits],
        "bdp_bytes_at_40ms_rtt": str(bdp_bytes),
        "window_bound_bits_per_second": str(window_bound),
    }, indent=2))


if __name__ == "__main__":
    main()
