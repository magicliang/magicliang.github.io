#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Bounded shared-channel contention model, not an IEEE 802.11 simulator."""
import argparse
import json
import platform
import random
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class Result:
    completed: int = 0
    dropped: int = 0
    pending: int = 0
    collision_rounds: int = 0
    idle_slots: int = 0
    busy_units: int = 0
    events: int = 0
    capped: bool = False
    completed_by_station: list[int] = field(default_factory=list)
    trace: list[tuple[str, int, tuple[int, ...]]] = field(default_factory=list)


class InvalidModelInput(ValueError):
    """The bounded model received inconsistent parameters."""


def simulate(backlog: tuple[int, ...], seed: int, initial: tuple[int, ...] | None = None,
             max_events: int = 20000, retry_limit: int = 4) -> Result:
    if not backlog or min(backlog) < 0 or max_events < 1 or retry_limit < 1:
        raise InvalidModelInput('nonnegative backlog, positive event and attempt limits required')
    rng = random.Random(seed)
    remaining = list(backlog)
    window = [3] * len(backlog)
    failures = [0] * len(backlog)
    counter = list(initial) if initial is not None else [rng.randrange(4) for _ in backlog]
    if len(counter) != len(backlog) or min(counter) < 0:
        raise InvalidModelInput('one nonnegative counter per station required')
    completed = dropped = collision_rounds = idle_slots = busy_units = events = 0
    completed_by_station = [0] * len(backlog)
    trace: list[tuple[str, int, tuple[int, ...]]] = []
    for _ in range(max_events):
        if not any(remaining):
            break
        events += 1
        contenders = tuple(i for i, n in enumerate(remaining) if n and counter[i] == 0)
        if not contenders:
            idle_slots += 1
            for i, n in enumerate(remaining):
                if n:
                    counter[i] -= 1
            continue
        busy_units += 5
        collision = len(contenders) > 1
        if collision:
            collision_rounds += 1
        if len(trace) < 12:
            trace.append(('collision' if collision else 'success',
                                 idle_slots + busy_units, contenders))
        for i in contenders:
            if collision:
                failures[i] += 1
                if failures[i] >= retry_limit:
                    dropped += 1
                    remaining[i] -= 1
                    failures[i] = 0
                    window[i] = 3
                else:
                    window[i] = min(2 * (window[i] + 1) - 1, 31)
            else:
                completed += 1
                completed_by_station[i] += 1
                remaining[i] -= 1
                failures[i] = 0
                window[i] = 3
            if remaining[i]:
                counter[i] = rng.randrange(window[i] + 1)
    pending = sum(remaining)
    capped = pending > 0
    assert completed + dropped + pending == sum(backlog)
    return Result(completed, dropped, pending, collision_rounds, idle_slots, busy_units,
                  events, capped, completed_by_station, trace)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20260919)
    args = parser.parse_args()
    single = simulate((30,), args.seed)
    shared = simulate((10, 10, 10), args.seed)
    assert single.completed == 30 and single.collision_rounds == 0
    forced = simulate((1, 1), 0, initial=(0, 0), retry_limit=1)
    assert forced.dropped == 2 and forced.collision_rounds == 1 and forced.busy_units == 5
    bounded = simulate((1,), 0, initial=(3,), max_events=1)
    assert bounded.pending == 1 and bounded.capped and bounded.idle_slots == 1
    freeze = simulate((1, 1), 0, initial=(0, 2))
    assert freeze.completed == 2 and freeze.idle_slots == 2 and freeze.busy_units == 10
    samples = [simulate((10, 10, 10), seed) for seed in range(10)]
    print(json.dumps({'scope': 'teaching model only; no radios, rates or real-time units',
                      'python': platform.python_version(), 'seed': args.seed,
                      'parameters': {'cw_min': 3, 'cw_max': 31, 'max_attempts_per_frame': 4,
                                     'busy_units_per_round': 5, 'max_events': 20000},
                      'single': asdict(single), 'shared': asdict(shared),
                      'selfchecks': ['forced collision and drop', 'event cap', 'freeze counter'],
                      'seeds_0_to_9': [asdict(s) for s in samples]}, indent=2))


if __name__ == '__main__':
    main()
