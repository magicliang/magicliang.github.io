#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 experiment.py (from this asset directory)
"""A bounded teaching frame: four-byte big-endian length and at most 4096 bytes."""
from __future__ import annotations

import struct
from typing import Final

MAX_FRAME: Final = 4096


class FrameTooLarge(ValueError):
    def __init__(self, size: int) -> None:
        super().__init__(f"frame length {size} exceeds {MAX_FRAME}")


class TruncatedFrame(EOFError):
    def __init__(self, buffered: int) -> None:
        super().__init__(f"EOF with {buffered} uncompleted bytes")


class Decoder:
    """Accumulate bounded chunks; a protocol error makes this instance unusable."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.expected: int | None = None

    def feed(self, chunk: bytes) -> list[bytes]:
        self.buffer.extend(chunk)
        messages: list[bytes] = []
        while True:
            if self.expected is None:
                if len(self.buffer) < 4:
                    return messages
                size = int.from_bytes(self.buffer[:4], "big")
                del self.buffer[:4]
                if size > MAX_FRAME:
                    raise FrameTooLarge(size)
                self.expected = size
            if len(self.buffer) < self.expected:
                return messages
            messages.append(bytes(self.buffer[:self.expected]))
            del self.buffer[:self.expected]
            self.expected = None

    def finish(self) -> None:
        if self.expected is not None or self.buffer:
            raise TruncatedFrame(len(self.buffer))


def encode(payload: bytes) -> bytes:
    if len(payload) > MAX_FRAME:
        raise FrameTooLarge(len(payload))
    return struct.pack("!I", len(payload)) + payload
