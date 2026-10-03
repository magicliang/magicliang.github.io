"""Publication DAG model + actual local HTTP manifest fetch; segments are fixtures, not encoded video."""
import functools
import hashlib
import http.server
import json
import sqlite3
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with sqlite3.connect(root/'tasks.db') as db:
            db.execute('CREATE TABLE done(video TEXT, profile TEXT, segment INTEGER, PRIMARY KEY(video,profile,segment))')
            db.execute('CREATE TABLE releases(video TEXT PRIMARY KEY NOT NULL, manifest TEXT)')
            expected={i:hashlib.sha256(f'PROTOCOL-FIXTURE-{i}'.encode()).hexdigest() for i in range(3)}
            for i in range(3):
                for retry in range(2):
                    db.execute('INSERT OR IGNORE INTO done VALUES(?,?,?)',('v','720p',i))
                (root/f'{i}.ts').write_bytes(f'PROTOCOL-FIXTURE-{i}'.encode())
            count=db.execute('SELECT count(*) FROM done').fetchone()[0]
            assert count==3
            def publish():
                if not all((root/f'{i}.ts').is_file() and hashlib.sha256((root/f'{i}.ts').read_bytes()).hexdigest()==expected[i] for i in range(3)):
                    return False
                text='#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXT-X-MEDIA-SEQUENCE:0\n'+''.join(f'#EXTINF:4.0,\n{i}.ts\n' for i in range(3))+'#EXT-X-ENDLIST\n'
                (root/'ready.tmp').write_text(text)
                (root/'ready.tmp').replace(root/'index.m3u8')
                db.execute('INSERT OR IGNORE INTO releases VALUES(?,?)',('v','index.m3u8'))
                return True
            (root/'1.ts').unlink()
            assert not publish()
            assert not (root/'index.m3u8').exists()
            assert db.execute('SELECT count(*) FROM releases').fetchone()[0]==0
            (root/'1.ts').write_bytes(b'corrupt')
            assert not publish()
            assert not (root/'index.m3u8').exists()
            assert db.execute('SELECT count(*) FROM releases').fetchone()[0]==0
            (root/'1.ts').write_bytes(b'PROTOCOL-FIXTURE-1')
            assert publish() and publish()
            assert db.execute('SELECT count(*) FROM releases').fetchone()[0]==1
        handler=functools.partial(Quiet,directory=str(root))
        with http.server.ThreadingHTTPServer(('127.0.0.1',0),handler) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}/'
            manifest=urllib.request.urlopen(base+'index.m3u8').read().decode()
            urls=[line for line in manifest.splitlines() if line and not line.startswith('#')]
            fetched=[urllib.request.urlopen(base+url).read().decode() for url in urls]
            assert fetched==[f'PROTOCOL-FIXTURE-{i}' for i in range(3)]
            (root/'1.ts').unlink()
            try:
                urllib.request.urlopen(base+'1.ts')
                missing=False
            except urllib.error.HTTPError as error:
                missing=error.code==404
            assert missing
            server.shutdown();thread.join()
        print(json.dumps(dict(task_rows=count,releases=1,missing_before_publish_rejected=True,corrupt_before_publish_rejected=True,http_segments=fetched,missing_segment_404=missing,playback='NOT_TESTED_PROTOCOL_FIXTURES')))
        if '--unsafe' in sys.argv:
            print('EXPECTED_REJECTION: published manifest with a missing segment is not a complete release')
            return 2
        print('PASS: task dedupe, single release, HTTP references and missing segment detection')
    return 0


if __name__=='__main__':
    sys.exit(main())
