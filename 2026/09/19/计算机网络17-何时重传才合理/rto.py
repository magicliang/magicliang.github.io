#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 rto.py
"""Exact arithmetic for two stipulated RTT samples; no socket or kernel model."""
import argparse
import json
from fractions import Fraction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    granularity = Fraction(1, 1000)
    samples = (Fraction(1, 10), Fraction(14, 100))
    srtt = samples[0]
    variation = samples[0] / 2
    rows = []
    for index, sample in enumerate(samples):
        if index:
            variation = Fraction(3, 4) * variation + Fraction(1, 4) * abs(srtt - sample)
            srtt = Fraction(7, 8) * srtt + Fraction(1, 8) * sample
        raw = srtt + max(granularity, 4 * variation)
        rows.append({'sample_ms': str(sample * 1000), 'srtt_ms': str(srtt * 1000),
                     'rttvar_ms': str(variation * 1000), 'raw_rto_ms': str(raw * 1000),
                     'rto_with_1s_floor_ms': str(max(Fraction(1), raw) * 1000)})
    assert rows[0] == {'sample_ms': '100', 'srtt_ms': '100', 'rttvar_ms': '50',
                       'raw_rto_ms': '300', 'rto_with_1s_floor_ms': '1000'}
    assert rows[1] == {'sample_ms': '140', 'srtt_ms': '105', 'rttvar_ms': '95/2',
                       'raw_rto_ms': '295', 'rto_with_1s_floor_ms': '1000'}
    # Counterexample: updating SRTT first produces the wrong variation for these inputs.
    wrong_variation = Fraction(3, 4) * Fraction(50) + Fraction(1, 4) * abs(Fraction(105) - 140)
    assert wrong_variation == Fraction(185, 4) and wrong_variation != variation * 1000
    timeout = 1000
    backoff = []
    for _ in range(2):
        timeout *= 2
        backoff.append(timeout)
    assert backoff == [2000, 4000]
    print(json.dumps({'units': 'milliseconds, exact rational strings', 'samples': rows,
                      'wrong_order_rttvar_ms': str(wrong_variation),
                      'two_timeouts_from_1s_ms': backoff}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
