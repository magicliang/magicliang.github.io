"""One real SQLite seat; all payment callbacks are local synthetic input."""
import concurrent.futures
import json
import platform
import sqlite3
import tempfile
import threading
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'tickets.db'
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE seat(id PRIMARY KEY,owner,state,expires); INSERT INTO seat VALUES(1,NULL,"free",0); CREATE TABLE orders(id PRIMARY KEY,state); CREATE TABLE callbacks(id PRIMARY KEY);')
    barrier=threading.Barrier(16)
    def hold(order):
        barrier.wait()
        with sqlite3.connect(path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE seat SET owner=?,state="held",expires=10 WHERE state="free"',(order,)).rowcount
            if changed:
                db.execute('INSERT INTO orders VALUES(?,"pending")',(order,))
            return changed
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        winners=sum(pool.map(hold,range(16)))
    assert winners==1
    with sqlite3.connect(path) as db:
        old=db.execute('SELECT owner FROM seat').fetchone()[0]
        db.execute('UPDATE orders SET state="expired" WHERE id=?',(old,))
        db.execute('UPDATE seat SET owner=99,state="held",expires=20 WHERE expires<=10')
        db.execute('INSERT INTO orders VALUES(99,"pending")')
    def callback(event,order,now):
        with sqlite3.connect(path) as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('INSERT OR IGNORE INTO callbacks VALUES(?)',(event,)).rowcount:
                return 'duplicate'
            sold=db.execute('UPDATE seat SET state="sold" WHERE owner=? AND state="held" AND expires>?',(order,now)).rowcount
            db.execute('UPDATE orders SET state=? WHERE id=?',('paid' if sold else 'refund_pending',order))
            return 'sold' if sold else 'refund_pending'
    late=callback('late',old,11)
    normal=callback('new',99,11)
    duplicate=callback('new',99,12)
    distinct=callback('new-distinct-id',99,12)
    assert distinct == 'already_paid_reconcile'
    with sqlite3.connect(path) as db:
        sold=db.execute('SELECT count(*) FROM seat WHERE state="sold"').fetchone()[0]
        paid=db.execute('SELECT count(*) FROM orders WHERE state="paid"').fetchone()[0]
    assert (late,normal,duplicate,sold,paid)==('refund_pending','sold','duplicate',1,1)
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'contenders':16,'holds':winners,'late_payment':late,'normal':normal,'duplicate':duplicate,'distinct_event':distinct,'sold_seats':sold,'paid_orders':paid,'pass':True}))
