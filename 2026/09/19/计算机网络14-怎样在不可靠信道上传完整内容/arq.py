#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 arq.py
"""Bounded deterministic selective-repeat teaching simulation; not TCP/TFTP."""
import argparse
import heapq
import json
from dataclasses import asdict, dataclass
from typing import Final, Literal, assert_never

BLOCKS: Final = tuple(f'block-{number};'.encode('ascii') for number in range(6))
WINDOW: Final = 3
TIMEOUT: Final = 4
ATTEMPTS: Final = 4
MAX_TICK: Final = 100
MAX_EVENTS: Final = 200
MAX_QUEUE: Final = 64


@dataclass(frozen=True, slots=True)
class Result:
    profile: str
    deduplication: bool
    sender_success: bool
    receiver_complete: bool
    stop_reason: str
    final_tick: int
    attempts: tuple[int, ...]
    application_order: tuple[int, ...]
    application_hex: str
    application_matches: bool
    trace: tuple[dict, ...]


def simulate(profile: Literal['combined', 'ack-loss', 'permanent'], deduplication: bool = True) -> Result:
    queue: list[tuple[int, int, Literal['DATA', 'ACK'], int, bytes]] = []
    attempts = [0] * len(BLOCKS)
    ack_counts = [0] * len(BLOCKS)
    acknowledged: set[int] = set()
    received: set[int] = set()
    cache: dict[int, bytes] = {}
    delivered: list[int] = []
    delivered_payloads: list[bytes] = []
    deadlines: dict[int, int] = {}
    trace: list[dict] = []
    base = next_block = receive_base = serial = processed = 0
    sender_success = False
    reason = 'tick-limit'
    tick = 0
    for tick in range(MAX_TICK + 1):
        while queue and queue[0][0] <= tick:
            _, _, kind, number, payload = heapq.heappop(queue)
            processed += 1
            assert processed <= MAX_EVENTS
            match kind:
                case 'DATA':
                    duplicate = number in received
                    received.add(number)
                    before = len(delivered)
                    if deduplication:
                        if number >= receive_base:
                            cache.setdefault(number, payload)
                        while receive_base in cache:
                            delivered_payloads.append(cache.pop(receive_base))
                            delivered.append(receive_base)
                            receive_base += 1
                    else:
                        delivered.append(number)
                        delivered_payloads.append(payload)
                    ack_counts[number] += 1
                    lost_ack = number in (1, 5) and ack_counts[number] == 1
                    trace.append({'tick': tick, 'event': 'receive-DATA', 'block': number,
                                  'duplicate': duplicate, 'payload_hex': payload.hex(),
                                  'receiver_cache': {index: data.hex() for index, data in sorted(cache.items())},
                                  'new_delivery': delivered[before:],
                                  'new_delivery_hex': [data.hex() for data in delivered_payloads[before:]],
                                  'delivery': list(delivered),
                                  'receiver_complete': len(received) == len(BLOCKS),
                                  'ack': 'dropped' if lost_ack else 'scheduled'})
                    if not lost_ack:
                        serial += 1
                        heapq.heappush(queue, (tick + 1, serial, 'ACK', number, b''))
                case 'ACK':
                    acknowledged.add(number)
                    deadlines.pop(number, None)
                    while base in acknowledged:
                        base += 1
                    trace.append({'tick': tick, 'event': 'receive-ACK', 'block': number,
                                  'base': base, 'next': next_block, 'acked': sorted(acknowledged)})
                case _:
                    assert_never(kind)
        if base == len(BLOCKS):
            sender_success, reason = True, 'all-blocks-acknowledged'
            break
        expired = [number for number, due in sorted(deadlines.items()) if due <= tick]
        exhausted = [number for number in expired if attempts[number] >= ATTEMPTS]
        if exhausted:
            reason = 'attempt-limit-block-' + str(exhausted[0])
            break
        send_now = list(expired)
        while next_block < min(base + WINDOW, len(BLOCKS)):
            send_now.append(next_block)
            next_block += 1
        assert next_block <= min(base + WINDOW, len(BLOCKS))
        for number in send_now:
            assert base <= number < base + WINDOW
            attempts[number] += 1
            deadlines[number] = tick + TIMEOUT
            lost = (profile == 'permanent' and number == 2) or (profile == 'combined' and number == 1 and attempts[number] == 1)
            delay = 3 if profile == 'combined' and number == 0 and attempts[number] == 1 else 1
            copies = 2 if profile == 'combined' and number == 2 and attempts[number] == 1 else 1
            trace.append({'tick': tick, 'event': 'send-DATA', 'block': number,
                          'attempt': attempts[number], 'base': base, 'next': next_block,
                          'deadline': deadlines[number], 'dropped': lost,
                          'delivery_delay': delay, 'copies': 0 if lost else copies})
            if not lost:
                for copy in range(copies):
                    serial += 1
                    heapq.heappush(queue, (tick + delay + copy, serial, 'DATA', number, BLOCKS[number]))
        assert len(queue) <= MAX_QUEUE and len(cache) <= WINDOW
        assert all(value <= ATTEMPTS for value in attempts)
    data = b''.join(delivered_payloads)
    return Result(profile, deduplication, sender_success, len(received) == len(BLOCKS), reason,
                  tick, tuple(attempts), tuple(delivered), data.hex(), data == b''.join(BLOCKS), tuple(trace))


def demo() -> None:
    combined = simulate('combined')
    permanent = simulate('permanent')
    protected = simulate('ack-loss')
    unprotected = simulate('ack-loss', False)
    expected = b''.join(BLOCKS).hex()
    for result in (combined, protected):
        assert result.sender_success and result.receiver_complete and result.application_matches
        assert result.application_order == tuple(range(6)) and result.application_hex == expected
    assert any(row.get('duplicate') for row in combined.trace)
    assert combined.attempts[1] == 3 and combined.attempts[5] == 2
    complete_tick = min(row['tick'] for row in combined.trace if row.get('receiver_complete'))
    assert complete_tick < combined.final_tick
    assert not permanent.sender_success and not permanent.receiver_complete
    assert permanent.stop_reason == 'attempt-limit-block-2' and permanent.attempts[2] == ATTEMPTS
    assert unprotected.sender_success and unprotected.receiver_complete
    assert not unprotected.application_matches and unprotected.application_hex != expected and len(unprotected.application_order) > 6
    protected_wire = [row for row in protected.trace if row['event'] in ('send-DATA', 'receive-ACK')]
    unprotected_wire = [row for row in unprotected.trace if row['event'] in ('send-DATA', 'receive-ACK')]
    assert protected_wire == unprotected_wire
    print(json.dumps({'scope': 'simulated events only; fixed ticks are not measured RTT/RTO or congestion control',
                      'bounds': {'blocks': 6, 'window': WINDOW, 'attempts_including_first': ATTEMPTS,
                                 'timer_ticks': TIMEOUT, 'max_tick': MAX_TICK,
                                 'max_processed_events': MAX_EVENTS, 'max_queue': MAX_QUEUE},
                      'expected_hex': expected,
                      'results': [asdict(result) for result in (combined, permanent, protected, unprotected)]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    demo()


if __name__ == '__main__':
    main()
