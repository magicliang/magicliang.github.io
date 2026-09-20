#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 policy.py
"""Offline single-prefix AS_SEQUENCE policy model, not a BGP implementation."""
import argparse
import json
from dataclasses import asdict, dataclass
from typing import Final

A: Final = 64512
B: Final = 64513
C: Final = 64514
PREFIX: Final = '203.0.113.0/24'


@dataclass(frozen=True, slots=True)
class Advertisement:
    sender: int
    path: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    neighbor: int
    path: tuple[int, ...]
    local_preference: int


@dataclass(frozen=True, slots=True)
class InvalidPolicy(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


def export(direction: tuple[int, int], path: tuple[int, ...], whitelist: frozenset[tuple[int, int]]) -> Advertisement | None:
    """Only explicitly permitted directional export prepends this sender."""
    sender, receiver = direction
    if direction not in whitelist:
        return None
    return Advertisement(sender, (sender,) + path)


def accept(receiver: int, update: Advertisement, imports: dict[tuple[int, int], int]) -> Candidate | None:
    """Imports set local preference locally; own-AS loops are rejected."""
    preference = imports.get((update.sender, receiver))
    if preference is None or receiver in update.path:
        return None
    if preference < 0 or not update.path or update.path[0] != update.sender:
        raise InvalidPolicy('preference must be nonnegative and AS_SEQUENCE must begin with sender')
    return Candidate(update.sender, update.path, preference)


def select(candidates: tuple[Candidate, ...]) -> Candidate | None:
    """Teaching order: local preference, path length, neighbor ASN tie-break."""
    if len({candidate.neighbor for candidate in candidates}) != len(candidates):
        raise InvalidPolicy('one current candidate per neighbor is required')
    return min(candidates, key=lambda item: (-item.local_preference, len(item.path), item.neighbor), default=None)


def demo(via_preference: int) -> None:
    exports = frozenset({(C, A), (C, B), (B, A)})
    imports = {(C, A): 100, (C, B): 100, (B, A): via_preference}
    direct = export((C, A), (), exports)
    to_b = export((C, B), (), exports)
    assert direct is not None and to_b is not None
    b_candidate = accept(B, to_b, imports)
    assert b_candidate is not None
    b_selected = select((b_candidate,))
    assert b_selected is not None
    to_a = export((B, A), b_selected.path, exports)
    assert to_a is not None and to_a.path == (B, C)
    a_direct = accept(A, direct, imports)
    a_via = accept(A, to_a, imports)
    assert a_direct is not None and a_via is not None
    candidates = (a_direct, a_via)
    first = select(candidates)
    assert first == a_via
    after_b_withdrawal = tuple(candidate for candidate in candidates if candidate.neighbor != B)
    second = select(after_b_withdrawal)
    assert second == a_direct
    after_c_withdrawal = tuple(candidate for candidate in after_b_withdrawal if candidate.neighbor != C)
    third = select(after_c_withdrawal)
    assert third is None
    no_b_export = export((B, A), b_selected.path, exports - {(B, A)})
    assert no_b_export is None
    without_b_export = select((a_direct,))
    assert without_b_export == a_direct
    no_b_import = accept(A, to_a, {(C, A): 100, (C, B): 100})
    assert no_b_import is None
    loop = accept(A, Advertisement(B, (B, A, C)), imports)
    assert loop is None
    print(json.dumps({'scope': 'offline single-prefix AS_SEQUENCE; next hops assumed reachable',
                      'prefix': PREFIX,
                      'export_whitelist': sorted(exports),
                      'import_policies': [{'sender': sender, 'receiver': receiver, 'local_preference': pref}
                                          for (sender, receiver), pref in sorted(imports.items())],
                      'announcements': [asdict(direct), asdict(to_b), asdict(to_a)],
                      'stages': [{'name': name, 'candidates': [asdict(item) for item in current],
                                  'selected': asdict(chosen) if chosen is not None else None}
                                 for name, current, chosen in (
                                     ('both-neighbors', candidates, first),
                                     ('withdraw-B-to-A', after_b_withdrawal, second),
                                     ('withdraw-C-to-A', after_c_withdrawal, third))],
                      'controls': {'B-export-policy-absent': no_b_export,
                                   'selected-without-B-export': asdict(without_b_export),
                                   'A-import-policy-absent-for-B': no_b_import,
                                   'own-AS-loop-rejected': loop is None},
                      'selection_order': ['higher locally assigned preference', 'shorter AS_SEQUENCE', 'lower neighbor ASN']}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--via-preference', type=int, default=200)
    args = parser.parse_args()
    if not 100 < args.via_preference <= 4294967295:
        parser.error('this demonstration requires 100 < via-preference <= 4294967295')
    demo(args.via_preference)


if __name__ == '__main__':
    main()
