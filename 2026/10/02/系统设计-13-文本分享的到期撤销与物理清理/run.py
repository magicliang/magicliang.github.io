"""Real SQLite metadata + local body; dictionaries model stale derived views."""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with sqlite3.connect(root/'meta.db') as db:
            db.execute('CREATE TABLE paste(id TEXT PRIMARY KEY NOT NULL, owner TEXT, expires INTEGER, revoked INTEGER)')
            db.executemany('INSERT INTO paste VALUES(?,?,?,0)', [('exp','alice',100),('rev','alice',200)])
            for key in ['exp','rev']:
                (root/key).write_text('private content')
            cache={'exp':'private content','rev':'private content'}
            index={'exp','rev'}
            def read(key,now,principal):
                owner,expires,revoked=db.execute('SELECT owner,expires,revoked FROM paste WHERE id=?',(key,)).fetchone()
                return cache[key] if principal==owner and now<expires and not revoked else None
            assert read('exp',99,'alice')=='private content'
            assert read('exp',99,'mallory') is None
            assert read('exp',100,'alice') is None
            db.execute('UPDATE paste SET revoked=1 WHERE id=?',('rev',))
            assert read('rev',99,'alice') is None
            stale=cache['rev']
            print(json.dumps(dict(expiry_boundary_denied=True,wrong_owner_denied=True,revoked_denied=True,stale_index=sorted(index),physical_body_before_gc=(root/'rev').exists())))
            for key in ['exp','rev']:
                (root/key).unlink(missing_ok=True)
                cache.pop(key,None)
                index.discard(key)
            assert not cache and not index and not (root/'rev').exists()
            print('PASS: logical denial precedes idempotent physical/derived cleanup')
            if '--unsafe' in sys.argv and stale:
                print('EXPECTED_REJECTION: old body cache alone bypasses revocation')
                return 2
    return 0


if __name__=='__main__':
    sys.exit(main())
