"""Real SQLite inventory state machine. Local fake payment IDs only."""
import json, sqlite3, tempfile, pathlib, platform
with tempfile.TemporaryDirectory() as tmp:
    db=sqlite3.connect(pathlib.Path(tmp)/'tickets.db')
    db.executescript('CREATE TABLE seats(id TEXT PRIMARY KEY, owner TEXT, state TEXT, expires INT); CREATE TABLE payments(id TEXT PRIMARY KEY, seat TEXT, owner TEXT); INSERT INTO seats VALUES("A1",NULL,"FREE",0);')
    def hold(owner,now):
        with db:
            return db.execute('UPDATE seats SET owner=?,state="HELD",expires=? WHERE id="A1" AND (state="FREE" OR (state="HELD" AND expires<=?))',(owner,now+10,now)).rowcount==1
    def pay(payment,owner,now):
        with db:
            prev=db.execute('SELECT seat,owner FROM payments WHERE id=?',(payment,)).fetchone()
            if prev: return 'duplicate' if prev==('A1',owner) else 'conflict'
            won=db.execute('UPDATE seats SET state="SOLD" WHERE id="A1" AND owner=? AND state="HELD" AND expires>?',(owner,now)).rowcount
            if not won: return 'refund_required'
            db.execute('INSERT INTO payments VALUES(?,"A1",?)',(payment,owner)); return 'sold'
    assert hold('alice',0) and not hold('bob',1)
    assert hold('bob',11)
    late=pay('p_old','alice',12); assert late=='refund_required'
    assert pay('p_new','bob',12)=='sold'
    assert pay('p_new','bob',13)=='duplicate'
    assert pay('p_new','eve',13)=='conflict'
    assert not hold('eve',30)
    row=db.execute('SELECT owner,state FROM seats').fetchone()
    assert row==('bob','SOLD') and db.execute('SELECT count(*) FROM payments').fetchone()[0]==1
    print(json.dumps(dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,
     late_payment=late,final=row,booked_payments=1,duplicate_safe=True,
     mismatched_key_rejected=True,pass_checks=True),indent=2))
