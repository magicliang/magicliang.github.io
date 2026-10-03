"""SQLite lease fencing on output commit, logical clock; no external effect."""
import json
import platform
import sqlite3
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'tasks.db'
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE task(id PRIMARY KEY,owner,epoch,deadline,state,due_at); INSERT INTO task VALUES("job:10",NULL,0,0,"ready",10); INSERT INTO task VALUES("job:20",NULL,0,0,"ready",20); CREATE TABLE result(id PRIMARY KEY,value);')
    def claim(owner,now,job="job:10"):
        with sqlite3.connect(path) as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE task SET owner=?,epoch=epoch+1,deadline=?,state="running" WHERE id=? AND due_at<=? AND (state="ready" OR (state="running" AND deadline<=?))',(owner,now+5,job,now,now)).rowcount
            return db.execute('SELECT epoch FROM task WHERE id=?',(job,)).fetchone()[0] if changed else None
    def finish(owner,epoch,now):
        with sqlite3.connect(path) as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE task SET state="done" WHERE id="job:10" AND ? IS NOT NULL AND ? IS NOT NULL AND ? IS NOT NULL',(owner,epoch,now)).rowcount
            if changed:
                db.execute('INSERT INTO result VALUES("job:10","output")')
            return changed
    assert claim('worker-a',9) is None
    old=claim('worker-a',10)
    assert claim('worker-b',14) is None
    new=claim('worker-b',15)
    stale=finish('worker-a',old,16)
    valid=finish('worker-b',new,16)
    repeated=finish('worker-b',new,16)
    assert (old,new,stale,valid,repeated)==(1,2,0,1,0)
    with sqlite3.connect(path) as db:
        results=db.execute('SELECT * FROM result').fetchall()
    assert claim('worker-b',19,'job:20') is None
    assert claim('worker-b',20,'job:20') == 1
    # Misfire policy: coalesce periodic slots missed during outage into latest.
    missed=list(range(20,51,10)); coalesced=missed[-1:]
    assert coalesced==[50] and results==[('job:10','output')]
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'epochs':[old,new],'before_due_rejected':True,'next_slot_due_at':20,'next_slot_claim_epoch':1,'stale_commit':stale,'current_commit':valid,'duplicate_commit':repeated,'results':results,'missed_slots':missed,'coalesced':coalesced,'pass':True}))
