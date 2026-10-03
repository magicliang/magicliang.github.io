"""Real SQLite backfill/upsert; single connection, deterministic schedule."""
import json, sqlite3, tempfile, pathlib, platform
with tempfile.TemporaryDirectory() as tmp:
    db=sqlite3.connect(pathlib.Path(tmp)/'migration.db')
    db.executescript('CREATE TABLE old(id TEXT PRIMARY KEY, value TEXT, version INT); CREATE TABLE new(id TEXT PRIMARY KEY, value TEXT, version INT); INSERT INTO old VALUES("s1","v1",1);')
    snapshot=db.execute('SELECT * FROM old').fetchall()
    db.execute('UPDATE old SET value="v2",version=2 WHERE id="s1"')
    db.execute('INSERT INTO new VALUES("s1","v2",2)'); db.commit()
    def merge(row):
        db.execute('INSERT INTO new VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value,version=excluded.version WHERE excluded.version>new.version',row)
    merge(snapshot[0]); db.commit()
    safe=db.execute('SELECT value,version FROM new').fetchone()
    assert safe==('v2',2)
    merge(('s1','DELETED',3)); merge(('s1','v2',2)); db.commit()
    tombstone=db.execute('SELECT value,version FROM new').fetchone()
    assert tombstone==('DELETED',3)
    db.execute('INSERT OR REPLACE INTO new VALUES(?,?,?)',snapshot[0]); db.commit()
    unsafe=db.execute('SELECT value,version FROM new').fetchone()
    assert unsafe==('v1',1)
    # New-only field makes old-format rollback lossy.
    rollback_allowed=set(['id','value','version','acl'])<=set(['id','value','version'])
    assert not rollback_allowed
    print(json.dumps(dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,
      safe=safe,tombstone=tombstone,negative_unconditional_backfill=unsafe,
      incompatible_rollback_allowed=rollback_allowed,pass_checks=True),indent=2))
