"""SQLite logical notifications and a fake channel with explicit uncertainty."""
import json
import platform
import sqlite3

with sqlite3.connect(':memory:') as db:
    db.executescript('CREATE TABLE notification(event,recipient,channel,state,attempts DEFAULT 0); CREATE TABLE preference(recipient PRIMARY KEY,enabled); INSERT INTO preference VALUES("u",1);')
    def enqueue(event):
        return db.execute('INSERT OR IGNORE INTO notification(event,recipient,channel,state) VALUES(?,"u","fake-mail","queued")',(event,)).rowcount
    assert enqueue('ok')==1 and enqueue('ok')==0
    enqueue('limited'); enqueue('uncertain'); enqueue('revoked')
    accepted_by_fake_channel=set()
    outcomes={'ok':['accepted'],'limited':['rate_limit','accepted'],'uncertain':['timeout_after_accept']}
    def attempt(event,now):
        if not db.execute('SELECT enabled FROM preference WHERE recipient="u"').fetchone()[0]:
            db.execute('UPDATE notification SET state="suppressed" WHERE event=?',(event,))
            return 'suppressed',None
        outcome=outcomes[event].pop(0)
        db.execute('UPDATE notification SET attempts=attempts+1 WHERE event=?',(event,))
        if outcome=='rate_limit':
            state,next_time='retry',now+3
        elif outcome=='timeout_after_accept':
            accepted_by_fake_channel.add(event)
            state,next_time='unknown',None
        else:
            accepted_by_fake_channel.add(event)
            state,next_time='accepted',None
        db.execute('UPDATE notification SET state=? WHERE event=?',(state,event))
        return state,next_time
    assert attempt('ok',0)==('accepted',None)
    assert attempt('limited',0)==('retry',3)
    assert attempt('limited',3)==('accepted',None)
    assert attempt('uncertain',0)==('unknown',None)
    # Provider lookup is simulated explicitly; no blind resend after timeout.
    assert 'uncertain' in accepted_by_fake_channel
    db.execute('UPDATE notification SET state="accepted" WHERE event="uncertain"')
    db.execute('UPDATE preference SET enabled=0')
    assert attempt('revoked',4)==('suppressed',None)
    rows=db.execute('SELECT event,state,attempts FROM notification ORDER BY event').fetchall()
    assert len(rows)==4 and len(accepted_by_fake_channel)==3
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'rows':rows,'fake_acceptances':sorted(accepted_by_fake_channel),'timeout_before_reconcile':'unknown','retry_not_before':3,'pass':True}))
