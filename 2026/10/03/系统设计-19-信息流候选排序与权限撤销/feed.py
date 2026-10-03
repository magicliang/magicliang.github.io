"""Stale candidate snapshot, deterministic score and authoritative SQLite privacy filter."""
import json
import sqlite3
import sys


def main():
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE posts(id TEXT PRIMARY KEY NOT NULL, owner TEXT, visibility TEXT, deleted INTEGER)')
        db.executemany('INSERT INTO posts VALUES(?,?,?,0)', [('p1','alice','public'),('p2','bob','public'),('p3','carol','public')])
        candidates=[('p1',10,3),('p2',8,9),('p3',5,4)]
        def feed(viewer,gate=True):
            ranked=sorted(candidates,key=lambda p:(-(2*p[1]+p[2]),p[0]))
            result=[]
            for key,affinity,freshness in ranked:
                owner,visibility,deleted=db.execute('SELECT owner,visibility,deleted FROM posts WHERE id=?',(key,)).fetchone()
                if not gate or (not deleted and (visibility=='public' or owner==viewer)):
                    result.append(key)
            return result
        if '--authority-down' in sys.argv:
            db.execute('DROP TABLE posts')
            try:
                feed('visitor')
            except sqlite3.OperationalError as error:
                print(json.dumps({'decision':'AUTHORITY_UNAVAILABLE','returned_candidates':[], 'error':str(error)}))
                return 3
            raise AssertionError('unavailable authority must not return a feed')
        before=feed('visitor')
        assert before==['p2','p1','p3']
        db.execute("UPDATE posts SET deleted=1 WHERE id='p2'")
        db.execute("UPDATE posts SET visibility='private' WHERE id='p1'")
        after=feed('visitor');owner=feed('alice');unsafe=feed('visitor',False)
        assert after==['p3'] and owner==['p1','p3']
        print(json.dumps(dict(before=before,stale_candidates=[p[0] for p in candidates],after=after,owner=owner,unsafe=unsafe,score='2*affinity+freshness')))
        if '--unsafe' in sys.argv:
            if 'p1' in unsafe or 'p2' in unsafe:
                print('EXPECTED_REJECTION: ranking stale candidates without authority gate leaks private/deleted posts')
                return 2
        print('PASS: deletion and privacy change override old candidates and scores')
    return 0


if __name__=='__main__':
    sys.exit(main())
