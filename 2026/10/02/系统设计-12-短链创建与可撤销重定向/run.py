"""Real concurrent SQLite inserts, separate connections and explicit collision."""
import concurrent.futures
import json
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'links.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE links(code TEXT PRIMARY KEY NOT NULL, target TEXT NOT NULL, active INTEGER NOT NULL)')
        barrier = threading.Barrier(12)
        def create(i):
            with sqlite3.connect(path, timeout=10) as db:
                barrier.wait()
                try:
                    db.execute('INSERT INTO links VALUES(?,?,1)', ('same', f'https://example.org/{i}'))
                    return 'created'
                except sqlite3.IntegrityError:
                    return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(create, range(12)))
        with sqlite3.connect(path) as db:
            winner = db.execute('SELECT target FROM links').fetchone()[0]
            cache = {'same': winner}
            db.execute('UPDATE links SET active=0 WHERE code=?', ('same',))
            active = db.execute('SELECT active FROM links WHERE code=?', ('same',)).fetchone()[0]
            safe = cache['same'] if active else None
            unsafe = cache['same']
            count = db.execute('SELECT count(*) FROM links').fetchone()[0]
        print(json.dumps(dict(created=results.count('created'), conflicts=results.count('conflict'), rows=count, winner=winner, revoked_safe=safe, revoked_cached=unsafe)))
        assert results.count('created') == count == 1
        assert results.count('conflict') == 11 and safe is None
        if '--unsafe' in sys.argv:
            if unsafe is not None:
                print('EXPECTED_REJECTION: cached redirect survives revocation')
                return 2
        print('PASS: unique insert never overwrites and authority gate denies revoked link')
    return 0


if __name__ == '__main__':
    sys.exit(main())
