#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 routing.py
"""Deterministic DV and asynchronous link-state teaching events; no protocol I/O."""
import argparse
import heapq
import json
from dataclasses import asdict, dataclass
from typing import Final

NODES: Final = ('A', 'B', 'C')
OLD: Final = (('A', 'B', 1), ('B', 'C', 1), ('A', 'C', 5))
NEW: Final = (('A', 'B', 1), ('A', 'C', 5))


@dataclass(frozen=True, slots=True)
class Choice:
    cost: int
    next_hop: str | None


def spf(source: str, edges: tuple[tuple[str, str, int], ...]) -> Choice:
    """Dijkstra to C; lexicographic first hop breaks equal-cost choices."""
    queue: list[tuple[int, str, str]] = [(0, '', source)]
    visited: set[str] = set()
    while queue:
        cost, first, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        if node == 'C':
            return Choice(cost, first or None)
        for left, right, weight in edges:
            if node in (left, right):
                neighbor = right if left == node else left
                heapq.heappush(queue, (cost + weight, first or neighbor, neighbor))
    raise AssertionError('this fixed graph must retain a route to C')


def trace(start: str, table: dict[str, Choice], edges: tuple[tuple[str, str, int], ...] = NEW) -> tuple[str, tuple[str, ...]]:
    """Follow installed hops, bounded by the number of graph vertices."""
    path: list[str] = []
    node = start
    for _ in range(len(NODES) + 1):
        if node in path:
            return 'loop', tuple(path + [node])
        path.append(node)
        if node == 'C':
            return 'delivered-in-model', tuple(path)
        hop = table[node].next_hop
        if hop is None:
            return 'no-route', tuple(path)
        if not any({node, hop} == {left, right} for left, right, _ in edges):
            return 'link-down', tuple(path + [hop])
        node = hop
    raise AssertionError('trace bound exceeded')


def demo(event_limit: int) -> None:
    assert event_limit >= 7
    table = {node: spf(node, OLD) for node in NODES}
    assert table == {'A': Choice(2, 'B'), 'B': Choice(1, 'C'), 'C': Choice(0, None)}
    cache = {'A': {'B': table['B'].cost, 'C': 0}, 'B': {'A': table['A'].cost}, 'C': {}}
    dv_events: list[dict] = []
    # After BC fails, B's former direct neighbor C is absent from its cache.
    for index, node in enumerate(('B', 'A', 'B', 'A', 'B', 'A', 'B'), 1):
        neighbor = 'A' if node == 'B' else 'B'
        cache[node][neighbor] = table[neighbor].cost
        alternatives = []
        for left, right, weight in NEW:
            if node in (left, right):
                peer = right if node == left else left
                alternatives.append((weight + cache[node][peer], peer))
        cost, hop = min(alternatives)
        previous = table[node]
        table[node] = Choice(cost, hop)
        state, path = trace('A', table)
        dv_events.append({'event': index, 'receiver': node, 'neighbor_cache': dict(cache[node]),
                          'previous': asdict(previous), 'computed': asdict(table[node]),
                          'installed': {name: asdict(choice) for name, choice in table.items()},
                          'trace_A': {'state': state, 'path': path}})
    assert [row['computed']['cost'] for row in dv_events[:5]] == [3, 4, 5, 5, 6]
    assert table['A'] == Choice(5, 'C') and table['B'] == Choice(6, 'A')
    assert dv_events[-2]['previous'] == dv_events[-2]['computed']
    assert dv_events[-1]['previous'] == dv_events[-1]['computed']
    assert dv_events[0]['trace_A']['state'] == 'loop'
    ls_table = {node: spf(node, OLD) for node in NODES}
    versions = {node: 1 for node in NODES}
    ls_events: list[dict] = []
    for index, node in enumerate(('B', 'A', 'B', 'A'), 1):
        versions[node] = 2
        previous = ls_table[node]
        computed = spf(node, NEW)
        ls_table[node] = computed
        state, path = trace('A', ls_table)
        ls_events.append({'event': index, 'router': node, 'topology_versions': dict(versions),
                          'previous': asdict(previous), 'computed': asdict(computed),
                          'installed': {name: asdict(choice) for name, choice in ls_table.items()},
                          'trace_A': {'state': state, 'path': path}})
    assert ls_events[0]['trace_A']['state'] == 'loop'
    assert ls_events[1]['trace_A']['state'] == 'delivered-in-model'
    assert ls_table['A'] == Choice(5, 'C') and ls_table['B'] == Choice(6, 'A')
    assert all(row['previous'] == row['computed'] for row in ls_events[-2:])
    reverse = {node: spf(node, OLD) for node in NODES}
    reverse['A'] = spf('A', NEW)
    reverse_state, reverse_path = trace('B', reverse)
    assert reverse_state == 'link-down' and reverse_path == ('B', 'C')
    print(json.dumps({'scope': 'teaching event schedule, not RIP/OSPF or a convergence-time benchmark',
                      'initial': {node: asdict(spf(node, OLD)) for node in NODES},
                      'destination': 'C', 'old_edges': OLD, 'new_edges': NEW,
                      'tie_rule': 'lexicographic next-hop name for equal total cost',
                      'event_limit': event_limit, 'dv': dv_events, 'ls': ls_events,
                      'reverse_ls_first_A': {'installed': {node: asdict(choice) for node, choice in reverse.items()},
                                            'trace_B': {'state': reverse_state, 'path': reverse_path}},
                      'fixed_point_checked': True}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event-limit', type=int, default=7)
    args = parser.parse_args()
    if args.event_limit < 7:
        parser.error('event-limit must be at least 7 for this fixed event schedule')
    demo(args.event_limit)


if __name__ == '__main__':
    main()
