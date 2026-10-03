"""Rollback after object upload: actual filesystem and SQLite transaction."""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with sqlite3.connect(root/'meta.db') as db:
            db.execute('CREATE TABLE photos(id TEXT PRIMARY KEY NOT NULL, object_key TEXT, state TEXT)')
            db.execute("INSERT INTO photos VALUES('p1','o1','PENDING')")
            db.commit()
            (root/'o1').write_bytes(b'original-image-fixture')
            try:
                with db:
                    db.execute("UPDATE photos SET state='READY' WHERE id='p1'")
                    raise RuntimeError('injected metadata failure before commit')
            except RuntimeError:
                pass
            visible=db.execute("SELECT id FROM photos WHERE state='READY'").fetchall()
            assert visible==[] and (root/'o1').exists()
            (root/'orphan').write_bytes(b'abandoned')
            # A pending session is still a reference; only expired/absent sessions are candidates.
            refs={r[0] for r in db.execute('SELECT object_key FROM photos')}
            candidates=['o1','orphan']
            removed=[]
            for key in candidates:
                if key not in refs:
                    (root/key).unlink();removed.append(key)
            assert removed==['orphan'] and (root/'o1').exists()
            with db:
                db.execute("UPDATE photos SET state='READY' WHERE id='p1' AND state='PENDING'")
            recovered=db.execute("SELECT id FROM photos WHERE state='READY'").fetchall()
            assert recovered==[('p1',)]
            print(json.dumps(dict(after_failure_visible=visible,removed=removed,after_retry_visible=recovered,pending_object_preserved=True)))
            if '--unsafe' in sys.argv:
                assert 'o1' in candidates
                print('EXPECTED_REJECTION: deleting all uploaded-but-not-ready objects destroys resumable session')
                return 2
            print('PASS: rollback hides half-finished photo; GC preserves referenced upload; retry publishes')
    return 0


if __name__=='__main__':
    sys.exit(main())
