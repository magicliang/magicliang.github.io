#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 udp.py
"""Bounded loopback UDP: explicit proxy injection, empty datagram and truncation."""
import argparse
import json
import platform
import socket
from contextlib import ExitStack
from typing import Final, Literal, assert_never

NUMBERS: Final[tuple[Literal[0, 1, 2, 3, 4], ...]] = (0, 1, 2, 3, 4)


def demo() -> None:
    events: list[dict] = []
    with ExitStack() as resources:
        sender, proxy, receiver = [resources.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) for _ in range(3)]
        for endpoint in (sender, proxy, receiver):
            endpoint.bind(('127.0.0.1', 0))
            endpoint.settimeout(2)
        addresses = {'sender': sender.getsockname(), 'proxy': proxy.getsockname(), 'receiver': receiver.getsockname()}
        buffered: bytes | None = None
        received: list[int] = []
        for number in NUMBERS:
            payload = str(number).encode('ascii')
            sent = sender.sendto(payload, addresses['proxy'])
            assert sent == len(payload)
            events.append({'event': 'sender-sendto-return', 'number': number, 'bytes': sent})
            actual, peer = proxy.recvfrom(100)
            assert peer == addresses['sender'] and actual == payload
            events.append({'event': 'proxy-recv', 'hex': actual.hex(), 'peer': peer})
            match number:
                case 0:
                    deliveries = (actual,)
                    action = 'forward'
                case 1:
                    deliveries = ()
                    action = 'drop'
                case 2:
                    buffered = actual
                    deliveries = ()
                    action = 'hold'
                case 3:
                    assert buffered is not None
                    deliveries = (actual, buffered)
                    action = 'forward-3-then-held-2'
                    buffered = None
                case 4:
                    deliveries = (actual, actual)
                    action = 'duplicate'
                case _:
                    assert_never(number)
            events.append({'event': 'injection', 'number': number, 'action': action})
            for delivery in deliveries:
                forwarded = proxy.sendto(delivery, addresses['receiver'])
                assert forwarded == len(delivery)
                events.append({'event': 'proxy-sendto-return', 'hex': delivery.hex(), 'bytes': forwarded})
                data, peer = receiver.recvfrom(100)
                assert peer == addresses['proxy'] and data == delivery
                received.append(int(data))
                events.append({'event': 'receiver-recv', 'hex': data.hex(), 'peer': peer})
        assert received == [0, 3, 2, 4, 4] and buffered is None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        for endpoint in (sender, receiver):
            endpoint.bind(('127.0.0.1', 0))
            endpoint.settimeout(2)
        target = receiver.getsockname()
        empty_sent = sender.sendto(b'', target)
        empty, peer = receiver.recvfrom(100)
        assert empty_sent == 0 and empty == b'' and peer == sender.getsockname()
        followup_sent = sender.sendto(b'after-empty', target)
        followup, peer = receiver.recvfrom(100)
        assert followup_sent == 11 and followup == b'after-empty' and peer == sender.getsockname()
        empty_result = {'sent_return': empty_sent, 'received_hex': empty.hex(), 'peer': peer,
                        'subsequent_hex': followup.hex(), 'meaning': 'empty datagram, not stream EOF'}
        truncation: dict = {'status': 'skipped', 'reason': 'recvmsg or MSG_TRUNC unavailable'}
        if hasattr(receiver, 'recvmsg') and hasattr(socket, 'MSG_TRUNC'):
            long_sent = sender.sendto(b'abcdefghij', target)
            data, ancillary, flags, peer = receiver.recvmsg(4)
            assert long_sent == 10 and data == b'abcd' and flags & socket.MSG_TRUNC
            assert peer == sender.getsockname() and not ancillary
            next_sent = sender.sendto(b'NEXT', target)
            next_data, next_peer = receiver.recvfrom(100)
            assert next_sent == 4 and next_data == b'NEXT' and next_peer == sender.getsockname()
            truncation = {'status': 'passed', 'sent_return': long_sent, 'buffer_bytes': 4,
                          'received_hex': data.hex(), 'flags': flags, 'MSG_TRUNC': socket.MSG_TRUNC,
                          'peer': peer, 'next_received_hex': next_data.hex()}
    print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
                      'scope': 'real loopback sockets; loss/reordering/duplication deliberately injected by application proxy',
                      'addresses': addresses, 'events': events, 'received_numbers': received,
                      'empty_datagram': empty_result, 'truncation': truncation}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    demo()


if __name__ == '__main__':
    main()
