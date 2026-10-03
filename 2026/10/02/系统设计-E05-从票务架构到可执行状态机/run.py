"""Real SQLite inventory state machine. Local fake payment IDs only."""
import json, sqlite3, tempfile, pathlib, platform
with tempfile.TemporaryDirectory() as tmp:
    db=sqlite3.connect(pathlib.Path(tmp)/'tickets.db')
    db.executescript('CREATE TABLE seats(id TEXT PRIMARY KEY, owner TEXT, hold_id TEXT, state TEXT, expires INT); CREATE TABLE payments(id TEXT PRIMARY KEY, seat TEXT, owner TEXT, hold_id TEXT); INSERT INTO seats VALUES("A1",NULL,NULL,"FREE",0);')
    def hold(owner,hold_id,now):
        with db:
            return db.execute('UPDATE seats SET owner=?,hold_id=?,state="HELD",expires=? WHERE id="A1" AND (state="FREE" OR (state="HELD" AND expires<=?))',(owner,hold_id,now+10,now)).rowcount==1
    def pay(payment,owner,hold_id,now):
        with db:
            prev=db.execute('SELECT seat,owner,hold_id FROM payments WHERE id=?',(payment,)).fetchone()
            if prev: return 'duplicate' if prev==('A1',owner,hold_id) else 'conflict'
            won=db.execute('UPDATE seats SET state="SOLD" WHERE id="A1" AND owner=? AND hold_id=? AND state="HELD" AND expires>?',(owner,hold_id,now)).rowcount
            if not won: return 'refund_required'
            db.execute('INSERT INTO payments VALUES(?,"A1",?,?)',(payment,owner,hold_id)); return 'sold'
    assert hold('alice','a1',0) and not hold('bob','b0',1)
    assert hold('bob','b1',11)
    late=pay('p_old','alice','a1',12); assert late=='refund_required'
    stale_same_owner=pay('p_stale','bob','b0',12); assert stale_same_owner=='refund_required'
    assert pay('p_new','bob','b1',12)=='sold'
    assert pay('p_new','bob','b1',13)=='duplicate'
    assert pay('p_new','eve','b1',13)=='conflict'
    assert pay('p_new','bob','other-hold',13)=='conflict'
    assert not hold('eve','e1',30)
    row=db.execute('SELECT owner,state FROM seats').fetchone()
    assert row==('bob','SOLD') and db.execute('SELECT count(*) FROM payments').fetchone()[0]==1
    def reset():
        with db:
            db.execute('DELETE FROM payments')
            db.execute('UPDATE seats SET owner=NULL,hold_id=NULL,state="FREE",expires=0')
    reset()
    assert hold('alice','first',0)
    expired_at_boundary=pay('expired','alice','first',10)
    assert expired_at_boundary=='refund_required'
    assert hold('alice','second',10)
    same_owner_old=pay('old','alice','first',11)
    assert same_owner_old=='refund_required'
    assert db.execute('SELECT hold_id,state FROM seats').fetchone()==('second','HELD')
    assert pay('new','alice','second',11)=='sold'
    assert pay('new','alice','first',12)=='conflict'
    assert db.execute('SELECT count(*) FROM payments').fetchone()[0]==1
    print(json.dumps(dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,
     expiry_equal_rejected=expired_at_boundary,same_owner_reacquired_old_payment=same_owner_old,late_payment=late,stale_hold_same_owner=stale_same_owner,final=row,booked_payments=1,duplicate_safe=True,
     mismatched_key_rejected=True,pass_checks=True),indent=2))
