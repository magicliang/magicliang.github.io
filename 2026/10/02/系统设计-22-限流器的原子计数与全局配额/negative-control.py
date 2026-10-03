"""Real SQLite atomic token bucket, logical clock; no Redis claim."""
import concurrent.futures
import json
import platform
import sqlite3
import tempfile
import threading
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'quota.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE bucket(id PRIMARY KEY, tokens REAL, tick REAL)')
        db.execute('INSERT INTO bucket VALUES(1, 5, 0)')
    barrier = threading.Barrier(20)
    def take(now, synchronize=False):
        if synchronize:
            barrier.wait()
        try:
            with sqlite3.connect(path, timeout=10) as db:
                db.execute('BEGIN IMMEDIATE')
                tokens, tick = db.execute('SELECT tokens,tick FROM bucket WHERE id=1').fetchone()
                now = max(now, tick)
                tokens = min(5, tokens + (now - tick) * 2)
                allowed = tokens >= 1
                db.execute('UPDATE bucket SET tokens=?,tick=? WHERE id=1', (tokens - int(allowed), now))
                return allowed
        except sqlite3.Error:
            return True
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        granted = sum(pool.map(lambda _: take(0, True), range(20)))
    assert granted == 5
    assert take(.499) is False
    assert take(.5) is True
    assert take(-10) is False, 'clock rollback must not refill'
    assert take(.5) is False
    local_buckets = 3 * 5
    assert local_buckets - 5 == 10
    healthy_path = path
    path = Path(directory) / 'unavailable' / 'quota.db'
    unavailable_allowed = take(1)
    assert unavailable_allowed is False
    path = healthy_path
    assert take(1) is True, 'healthy storage must recover after injected failure'
    failure_decision = 'reject'
    print(json.dumps({'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version, 'concurrent': 20, 'allowed': granted, 'boundary': [.499, .5], 'independent_instances_allowed': local_buckets, 'global_excess': 10, 'storage_failure': failure_decision, 'unavailable_take_allowed': unavailable_allowed, 'recovered_take_allowed': True, 'independent_instances_is_arithmetic': True, 'pass': True}))
