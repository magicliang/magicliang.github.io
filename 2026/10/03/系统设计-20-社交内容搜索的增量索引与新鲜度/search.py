"""Actual SQLite FTS5 index, explicit out-of-order versions and measured local indexing delay."""
import json
import sqlite3
import sys
import time


def scenario(guarded, stalled=False):
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE state(id TEXT PRIMARY KEY NOT NULL, version INTEGER, deleted INTEGER)')
        db.execute('CREATE VIRTUAL TABLE docs USING fts5(id UNINDEXED, body)')
        events=[('p',1,'red apple',False),('p',3,'blue berry',False),('p',2,'red orange',False),('p',4,'',True),('p',3,'blue berry',False),('q',1,'blue sky',False)]
        trace=[]
        for key,version,body,deleted in events:
            published=time.monotonic_ns()
            time.sleep(.01)  # deliberate local queue delay; no throughput claim
            old=db.execute('SELECT version FROM state WHERE id=?',(key,)).fetchone()
            accepted=not guarded or old is None or version>old[0]
            if stalled and key == 'p' and version > 1:
                accepted = False
            if accepted:
                with db:
                    db.execute('INSERT INTO state VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,deleted=excluded.deleted',(key,version,int(deleted)))
                    db.execute('DELETE FROM docs WHERE id=?',(key,))
                    if not deleted:
                        db.execute('INSERT INTO docs VALUES(?,?)',(key,body))
            hits=[r[0] for r in db.execute("SELECT id FROM docs WHERE docs MATCH 'blue'")]
            red_hits=[r[0] for r in db.execute("SELECT id FROM docs WHERE docs MATCH 'red'")]
            lag=(time.monotonic_ns()-published)/1e6
            trace.append(dict(id=key,version=version,accepted=accepted,blue_hits=hits,red_hits=red_hits,publish_to_query_ms=round(lag,3)))
        final=[r[0] for r in db.execute("SELECT id FROM docs WHERE docs MATCH 'blue'")]
        if stalled:
            state = db.execute("SELECT version,deleted FROM state WHERE id='p'").fetchone()
            assert state == (1, 0)
            assert db.execute("SELECT id FROM docs WHERE docs MATCH 'red'").fetchall() == [('p',)]
        return trace,final


if __name__=='__main__':
    if '--stalled' in sys.argv:
        trace, final = scenario(True, True)
        assert trace[1]['blue_hits'] == [] and trace[3]['blue_hits'] == []
        print(json.dumps({'stalled':trace, 'final':final, 'edit_visible':False, 'delete_applied':False, 'edit_publish_to_visible_ms':None, 'delete_publish_to_visible_ms':None}))
        print('INDEX_STALLED: edit and delete remain unapplied; latency is unobserved, not zero')
        sys.exit(3)
    good,final=scenario(True)
    bad,unsafe=scenario(False)
    print(json.dumps(dict(versioned=good,final=final,unversioned_final=unsafe)))
    assert final==['q'] and unsafe==['p','q']
    assert good[2]['accepted'] is False and good[4]['accepted'] is False
    assert good[0]['red_hits']==['p']
    assert good[1]['red_hits']==[] and good[3]['red_hits']==[]
    assert good[1]['blue_hits']==['p'] and good[3]['blue_hits']==[]
    if '--unsafe' in sys.argv:
        print('EXPECTED_REJECTION: stale edit resurrected deleted document without version tombstone')
        sys.exit(2)
    print('PASS: edits searchable, stale versions ignored, tombstone prevents resurrection; FTS5 queried after each event')
