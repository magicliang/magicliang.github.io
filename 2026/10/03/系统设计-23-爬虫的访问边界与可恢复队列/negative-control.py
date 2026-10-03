"""Local HTTP only; persistent frontier, robots, bounded calendar trap."""
import http.server
import json
import platform
import sqlite3
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

seen_requests = []
retry_count = 0
class Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global retry_count
        seen_requests.append((self.path, time.monotonic()))
        status = 200
        if self.path == '/robots.txt':
            body = 'User-agent: *\nDisallow: /private\n'
        elif self.path == '/':
            body = '/page#one\n/page#two\n/private\n/retry\n/calendar/1\nhttps://example.org/no'
        elif self.path == '/retry':
            retry_count += 1
            status = 503 if retry_count == 1 else 200
            body = ''
        elif self.path.startswith('/calendar/'):
            body = '/calendar/' + str(int(self.path.rsplit('/', 1)[1]) + 1)
        else:
            body = ''
        payload = body.encode()
        self.send_response(status)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def log_message(self, *args):
        pass

with tempfile.TemporaryDirectory() as directory:
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Site)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError('redirect outside local fixture is forbidden')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    last = 0.0
    def fetch(url):
        global last
        assert urllib.parse.urlsplit(url).netloc == urllib.parse.urlsplit(origin).netloc
        time.sleep(max(0, .03 - (time.monotonic() - last)))
        try:
            with opener.open(url, timeout=2) as response:
                return response.read(65536).decode()
        finally:
            last = time.monotonic()
    try:
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(fetch(origin + '/robots.txt').splitlines())
        path = Path(directory) / 'frontier.db'
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE frontier(url PRIMARY KEY,state,attempts)')
        def enqueue(raw):
            url = urllib.parse.urldefrag(urllib.parse.urljoin(origin, raw))[0]
            parts = urllib.parse.urlsplit(url)
            if parts.scheme != 'http' or parts.netloc != urllib.parse.urlsplit(origin).netloc:
                return
            if parts.path.startswith('/calendar/') and int(parts.path.rsplit('/', 1)[1]) > 3:
                return
            if True:
                db.execute('INSERT OR IGNORE INTO frontier VALUES(?,"queued",0)', (url,))
        enqueue('/')
        db.commit()
        def step(crash=False):
            row = db.execute('SELECT url,attempts FROM frontier WHERE state="queued" ORDER BY url LIMIT 1').fetchone()
            if not row:
                return False
            url, attempts = row
            db.execute('UPDATE frontier SET state="running",attempts=attempts+1 WHERE url=?', (url,))
            db.commit()
            if crash:
                return True
            try:
                body = fetch(url)
                for raw in body.splitlines():
                    enqueue(raw)
                state = 'done'
            except urllib.error.HTTPError as error:
                assert error.code == 503
                state = 'queued' if attempts < 2 else 'failed'
            db.execute('UPDATE frontier SET state=? WHERE url=?', (state, url))
            db.commit()
            return True
        step()
        step(crash=True)
        db.close()
        db = sqlite3.connect(path)
        recovering = db.execute('SELECT count(*) FROM frontier WHERE state="running"').fetchone()[0]
        db.execute('UPDATE frontier SET state="queued" WHERE state="running"')
        db.commit()
        while step():
            pass
        rows = db.execute('SELECT url,state,attempts FROM frontier ORDER BY url').fetchall()
        db.close()
        paths = [p for p, _ in seen_requests]
        intervals = [b[1]-a[1] for a,b in zip(seen_requests, seen_requests[1:])]
        assert recovering == 1 and all(row[1] == 'done' for row in rows)
        assert '/private' not in paths and paths.count('/page') == 1
        assert '/calendar/3' in paths and '/calendar/4' not in paths
        assert retry_count == 2 and min(intervals) >= .028
        print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'paths':paths,'minimum_interval_seconds':min(intervals),'recovered_running':recovering,'frontier_rows':len(rows),'retry_attempts':retry_count,'pass':True}))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
