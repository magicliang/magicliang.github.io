"""Deterministic virtual-time retry model; no real sockets or latency benchmark."""
import json
import sys


def run(guarded, requests=100, budget=250, cost=100):
    calls = rejected = 0
    elapsed = []
    for request in range(requests):
        if guarded and request >= 20:  # admission budget for this fixed burst
            rejected += 1
            continue
        used = 0
        for outer in range(1 if guarded else 3):
            for inner in range(2 if guarded else 3):
                wait = 20 if inner else 0
                if guarded and used + wait + cost > budget:
                    break
                used += wait + cost
                calls += 1
        elapsed.append(used)
    return dict(calls=calls, rejected=rejected, max_elapsed_ms=max(elapsed))


if __name__ == '__main__':
    naive, bounded = run(False), run(True)
    short = run(True, budget=150)
    print(json.dumps(dict(naive=naive, bounded=bounded, shorter_deadline=short)))
    assert naive['calls'] == 900 and bounded['calls'] == 40
    assert bounded['max_elapsed_ms'] == 220 and short['calls'] == 20
    assert bounded['rejected'] == 80
    if '--unsafe' in sys.argv:
        if naive['calls'] > 40:
            print('EXPECTED_REJECTION: nested retries exceed downstream budget')
            sys.exit(2)
    print('PASS: call budget, deadline and admission bounds hold in virtual time')
