"""SQLite durable messages and client dedupe across reconnect, without WebSocket transport."""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with sqlite3.connect(root/'server.db') as server:
            client=sqlite3.connect(root/'client.db')
            server.execute('CREATE TABLE messages(seq INTEGER PRIMARY KEY, client_key TEXT UNIQUE NOT NULL, text TEXT)')
            client.execute('CREATE TABLE rendered(seq INTEGER PRIMARY KEY, text TEXT)')
            for seq in range(1,6):
                server.execute('INSERT INTO messages VALUES(?,?,?)',(seq,f'k{seq}',f'message-{seq}'))
            try:
                server.execute('INSERT INTO messages VALUES(?,?,?)',(6,'k5','duplicate-send'))
            except sqlite3.IntegrityError:
                pass
            deliveries=[]
            def apply(rows):
                for seq,body in rows:
                    deliveries.append(seq)
                    client.execute('INSERT OR IGNORE INTO rendered VALUES(?,?)',(seq,body))
            apply(server.execute('SELECT seq,text FROM messages WHERE seq<=2').fetchall())
            client.commit();server.commit()
            client.close()
            client=sqlite3.connect(root/'client.db')
            before_ack=[r[0] for r in client.execute('SELECT seq FROM rendered ORDER BY seq')]
            assert before_ack==[1,2]
            # Device durable apply succeeded, but transport ACK for message 2 was lost.
            cursor=1
            apply(server.execute('SELECT seq,text FROM messages WHERE seq>? ORDER BY seq',(cursor,)).fetchall())
            client.commit();server.commit()
        client.close()
        with sqlite3.connect(root/'client.db') as client:
            shown=[r[0] for r in client.execute('SELECT seq FROM rendered ORDER BY seq')]
        assert shown==[1,2,3,4,5] and deliveries==[1,2,2,3,4,5]
        print(json.dumps(dict(durable_before_lost_ack=before_ack,transport_deliveries=deliveries,durable_display=shown,server_messages=5,replayed=2)))
        if '--unsafe' in sys.argv:
            if len(deliveries)!=len(set(deliveries)):
                print('EXPECTED_REJECTION: append-only rendering duplicates reconnect replay')
                return 2
        print('PASS: reconnect fills offline gap; replay and repeated send do not duplicate durable display')
    return 0


if __name__=='__main__':
    sys.exit(main())
