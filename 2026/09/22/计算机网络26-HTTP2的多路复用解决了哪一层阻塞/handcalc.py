#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Offline window arithmetic and one bounded HPACK index example; not a decoder."""
import argparse
import json


def verify() -> None:
    connection, stream1, stream3 = 12, 8, 10
    first = min(connection, stream1)
    connection -= first
    stream1 -= first
    second = min(connection, stream3)
    connection -= second
    stream3 -= second
    assert (first, second, connection, stream1, stream3) == (8, 4, 0, 0, 6)
    stream1 += 8
    assert min(connection, stream1) == 0
    connection += 5
    assert min(connection, stream1) == 5
    print(json.dumps({'type': 'offline_arithmetic', 'sent': [first, second],
                      'after_stream_update_allowed': 0, 'after_connection_update_allowed': 5}))
    authority = b'www.example.com'
    literal = bytes.fromhex('410f') + authority
    assert len(authority) == 15 and len(literal) == 17
    assert literal[0] == 0x40 + 1  # Incremental indexing, static name index 1.
    assert literal[1] & 0x80 == 0  # This example does not use Huffman coding.
    table_size = len(b':authority') + len(authority) + 32
    assert table_size == 57
    repeated = bytes([0x80 | 62])  # Static table has 61 entries; newest dynamic is 62.
    assert repeated.hex() == 'be'
    print(json.dumps({'type': 'bounded_hpack_handcalculation', 'literal_hex': literal.hex(),
                      'dynamic_entry_accounting_bytes': table_size, 'later_index_hex': repeated.hex(),
                      'requires_same_direction_prior_table_state': True}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    verify()


if __name__ == '__main__':
    main()
