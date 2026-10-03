"""SQLite conditional dispatch with assignment generation and logical time."""
import concurrent.futures
import json
import platform
import sqlite3
import tempfile
import threading
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'dispatch.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE driver(id PRIMARY KEY,owner,state,generation,deadline)')
        db.execute('INSERT INTO driver VALUES(1,NULL,"idle",0,0)')
    barrier=threading.Barrier(12)
    def offer(order):
        barrier.wait()
        with sqlite3.connect(path,timeout=10) as db:
            return db.execute('UPDATE driver SET owner=?,state="offered",generation=generation+1,deadline=10 WHERE id=1',(order,)).rowcount
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        accepted=sum(pool.map(offer,range(12)))
    assert accepted==1
    with sqlite3.connect(path) as db:
        old_owner,old_generation=db.execute('SELECT owner,generation FROM driver').fetchone()
        expired=db.execute('UPDATE driver SET owner=NULL,state="idle" WHERE state="offered" AND deadline<=10').rowcount
        db.execute('UPDATE driver SET owner=99,state="offered",generation=generation+1,deadline=20 WHERE state="idle"')
        stale=db.execute('UPDATE driver SET state="accepted" WHERE owner=? AND generation=? AND state="offered" AND deadline>11',(old_owner,old_generation)).rowcount
        current=db.execute('UPDATE driver SET state="accepted" WHERE owner=99 AND generation=2 AND state="offered" AND deadline>11').rowcount
        cancelled=db.execute('UPDATE driver SET owner=NULL,state="idle" WHERE owner=99 AND generation=2 AND state="accepted"').rowcount
        late_after_cancel=db.execute('UPDATE driver SET state="accepted" WHERE owner=99 AND generation=2 AND state="offered"').rowcount
        state=db.execute('SELECT state FROM driver').fetchone()[0]
    assert (expired,stale,current,cancelled,late_after_cancel,state)==(1,0,1,1,0,'idle')
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'contenders':12,'offers':accepted,'stale_ack_rows':stale,'current_ack_rows':current,'cancel_rows':cancelled,'late_after_cancel':late_after_cancel,'pass':True}))
