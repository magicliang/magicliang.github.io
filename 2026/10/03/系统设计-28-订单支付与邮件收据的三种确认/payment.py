"""Real SQLite order/outbox transaction; separate fake provider ledger."""
import json
import platform
import sqlite3
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'orders.db'
    provider=sqlite3.connect(Path(directory)/'fake-provider.db')
    provider.execute('CREATE TABLE charges(id PRIMARY KEY,amount,state)')
    provider.commit()
    db=sqlite3.connect(path)
    db.executescript('CREATE TABLE orders(id PRIMARY KEY,amount,state); CREATE TABLE payment(id PRIMARY KEY,amount,state); CREATE TABLE outbox(id PRIMARY KEY,kind); CREATE TABLE inbox(id PRIMARY KEY); CREATE TABLE receipt(id PRIMARY KEY,state);')
    def create(order,amount,fail=False):
        try:
            with db:
                db.execute('INSERT INTO orders VALUES(?,?,"pending")',(order,amount))
                if fail:
                    raise RuntimeError('injected before outbox')
                db.execute('INSERT INTO outbox VALUES(?,"request_payment")',(order,))
        except RuntimeError:
            return False
        return True
    assert not create('rollback',100,True)
    assert db.execute('SELECT count(*) FROM orders').fetchone()[0]==0
    assert create('o1',100)
    def charge(order,amount,lose_reply=False):
        with provider:
            provider.execute('INSERT OR IGNORE INTO charges VALUES(?,?,"succeeded")',(order,amount))
            prior=provider.execute('SELECT amount FROM charges WHERE id=?',(order,)).fetchone()[0]
            if prior!=amount:
                raise ValueError('idempotency parameter mismatch')
        if lose_reply:
            raise TimeoutError('accepted but response lost')
    try:
        charge('o1',100,True)
    except TimeoutError:
        pass
    assert db.execute('SELECT state FROM orders WHERE id="o1"').fetchone()[0]=='pending'
    assert provider.execute('SELECT count(*) FROM charges').fetchone()[0]==1
    db.close()
    db=sqlite3.connect(path)
    charge('o1',100)
    try:
        charge('o1',200)
    except ValueError:
        mismatch=True
    def callback(event,state):
        with db:
            if not db.execute('INSERT OR IGNORE INTO inbox VALUES(?)',(event,)).rowcount:
                return
            if state=='succeeded':
                db.execute('INSERT OR IGNORE INTO payment VALUES("o1",100,"succeeded")')
                db.execute('UPDATE orders SET state="paid" WHERE id="o1" AND state="pending"')
                db.execute('INSERT OR IGNORE INTO outbox VALUES("paid:o1","order_paid")')
                db.execute('INSERT OR IGNORE INTO receipt VALUES("receipt:o1","queued")')
            # Pending is informational; cannot regress a terminal success.
    callback('e2','succeeded'); callback('e2','succeeded'); callback('e1','pending')
    local=db.execute('SELECT id,amount,state FROM orders').fetchall()
    remote=provider.execute('SELECT id,amount,state FROM charges').fetchall()
    outbox=db.execute('SELECT * FROM outbox ORDER BY id').fetchall()
    assert mismatch and local==[('o1',100,'paid')] and remote==[('o1',100,'succeeded')]
    assert len(outbox)==2 and db.execute('SELECT count(*) FROM payment').fetchone()[0]==1
    # Receipt state is local synthetic input, never a delivery confirmation.
    db.execute('UPDATE receipt SET state="accepted_by_fake_channel" WHERE id="receipt:o1"')
    db.execute('UPDATE receipt SET state="bounced" WHERE id="receipt:o1"')
    receipt=db.execute('SELECT id,state FROM receipt').fetchall()
    assert receipt==[('receipt:o1','bounced')]
    assert db.execute('SELECT state FROM orders WHERE id="o1"').fetchone()[0]=='paid'
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'local':local,'receipt':receipt,'fake_provider':remote,'outbox':outbox,'lost_reply_local_pending_remote_charged':True,'rollback_left_zero_orders':True,'mismatch_rejected':mismatch,'pass':True}))
    db.close(); provider.close()
