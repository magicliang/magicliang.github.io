"""Filesystem chunk resume and real SQLite compare-and-swap version conflict."""
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


def main():
    digest=lambda b:hashlib.sha256(b).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        body=b''.join(bytes([i])*1024 for i in range(8))
        parts=[body[i:i+1024] for i in range(0,len(body),1024)]
        manifest=[digest(p) for p in parts]
        (root/manifest[0]).write_bytes(parts[0])  # simulated interruption after first upload
        uploaded=0
        for key,part in zip(manifest,parts):
            if not (root/key).exists():
                (root/key).write_bytes(part);uploaded+=1
            assert digest((root/key).read_bytes())==key
        restored=b''.join((root/key).read_bytes() for key in manifest)
        assert restored==body
        # Corrupt one stored chunk, detect it before publishing a new manifest.
        (root/manifest[0]).write_bytes(b'corrupt')
        corrupt_detected=digest((root/manifest[0]).read_bytes())!=manifest[0]
        assert corrupt_detected
        (root/manifest[0]).write_bytes(parts[0])
        with sqlite3.connect(root/'versions.db') as db:
            db.execute('CREATE TABLE files(id TEXT PRIMARY KEY NOT NULL, version INTEGER, hash TEXT)')
            db.execute('CREATE TABLE conflicts(device TEXT PRIMARY KEY NOT NULL, base INTEGER, hash TEXT)')
            db.execute('INSERT INTO files VALUES(?,?,?)',('f',1,digest(body)))
            for payload in [b'edit A',b'edit B']:
                (root/digest(payload)).write_bytes(payload)
            a,b=digest(b'edit A'),digest(b'edit B')
            assert db.execute('UPDATE files SET version=version+1,hash=? WHERE id=? AND version=?',(a,'f',1)).rowcount==1
            changed=db.execute('UPDATE files SET version=version+1,hash=? WHERE id=? AND version=?',(b,'f',1)).rowcount
            if changed==0:
                db.execute('INSERT INTO conflicts VALUES(?,?,?)',('B',1,b))
            current=db.execute('SELECT version,hash FROM files').fetchone()
            conflict=db.execute('SELECT device,base,hash FROM conflicts').fetchone()
            assert current==(2,a) and conflict==('B',1,b)
        with sqlite3.connect(root/'versions.db') as db:
            current_key=db.execute('SELECT hash FROM files').fetchone()[0]
            conflict_key=db.execute('SELECT hash FROM conflicts').fetchone()[0]
        recovered_edits=[(root/key).read_bytes() for key in [current_key,conflict_key]]
        assert recovered_edits==[b'edit A',b'edit B']
        assert [digest(payload) for payload in recovered_edits]==[current_key,conflict_key]
        print(json.dumps(dict(file_sha256=digest(restored),bytes=len(restored),unique_chunks=len(set(manifest)),extra_uploads_after_resume=uploaded,corruption_detected=corrupt_detected,current_version=current[0],conflict_device=conflict[0],recovered_edits=[p.decode() for p in recovered_edits])))
        if '--unsafe' in sys.argv:
            if b!=current[1]:
                print('EXPECTED_REJECTION: last-writer-wins would discard edit A without conflict copy')
                return 2
        print('PASS: resume preserves bytes; corrupt chunk rejected; concurrent base retains both edits')
    return 0


if __name__=='__main__':
    sys.exit(main())
