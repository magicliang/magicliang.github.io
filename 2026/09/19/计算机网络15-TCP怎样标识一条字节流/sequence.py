#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Finite hand calculation of a TCP sequence example; not a TCP implementation."""
import argparse
import json
from typing import TypeAlias


JsonValue: TypeAlias = str | int | list["JsonValue"] | dict[str, "JsonValue"]


class SequenceRangeError(ValueError):
    """A hand-calculation operand is outside the supported range."""


MODULUS = 1 << 32


def after(seq: int, data_length: int, syn: bool = False, fin: bool = False) -> int:
    if not 0 <= seq < MODULUS or not 0 <= data_length < MODULUS:
        raise SequenceRangeError('sequence and length must fit unsigned 32-bit values')
    return (seq + data_length + int(syn) + int(fin)) % MODULUS


def demo() -> dict[str, JsonValue]:
    # This fixed trace excludes wrap, invalid segments, buffer eviction and windows.
    next_expected = after(1000, 0, syn=True)
    pending: dict[int, int] = {}
    delivered = bytearray()
    rows: list[dict[str, JsonValue]] = [
        {'event': 'SYN', 'seq': 1000, 'ack_state': next_expected, 'sack': []}
    ]
    for seq, payload in ((1005, b'EFGH'), (1001, b'ABCD')):
        for offset, byte in enumerate(payload):
            pending[seq + offset] = byte
        while next_expected in pending:
            delivered.append(pending.pop(next_expected))
            next_expected += 1
        sack = [[min(pending), max(pending) + 1]] if pending else []
        rows.append({'event': 'DATA', 'seq': seq, 'payload_hex': payload.hex(),
                     'ack_state': next_expected, 'sack': sack,
                     'delivered_hex': delivered.hex()})
    assert next_expected == 1009 and delivered == b'ABCDEFGH' and not pending
    next_expected = after(next_expected, 0, fin=True)
    rows.append({'event': 'FIN', 'seq': 1009, 'ack_state': next_expected, 'sack': []})
    assert [row['ack_state'] for row in rows] == [1001, 1001, 1009, 1010]
    assert rows[1]['sack'] == [[1005, 1009]]
    pure_ack_after = after(3000, 0)
    wrapped_after = after(MODULUS - 2, 4)
    assert pure_ack_after == 3000 and wrapped_after == 2
    return {'boundary': 'hand calculation only; ACK states are not emitted packets',
            'trace': rows, 'pure_ack_after': pure_ack_after,
            'wrap_example_after': wrapped_after}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(demo(), indent=2))
