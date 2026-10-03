"""Real loopback HTTP SSE producer/client, bounded slots, explicit cancellation.
Tokens are numbered mock chunks, not tokenizer tokens or provider billing units.
"""
import http.client
import json
import platform
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

lock = threading.Lock()
runs = {}
limit = threading.BoundedSemaphore(1)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        key = self.path.removeprefix('/cancel/')
        with lock:
            state = runs.get(key)
        if state:
            state['cancel'].set()
        self.send_response(202 if state else 404)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        key = self.path.removeprefix('/stream/')
        with lock:
            duplicate = key in runs
        if duplicate or not limit.acquire(blocking=False):
            self.send_response(409 if duplicate else 429)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        state = {'generated': 0, 'written': 0, 'cancel': threading.Event(), 'done': threading.Event()}
        with lock:
            runs[key] = state
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            for seq in range(20):
                if state['cancel'].wait(.015):
                    break
                state['generated'] += 1
                self.wfile.write(f'id: {seq}\ndata: {seq}\n\n'.encode())
                self.wfile.flush()
                state['written'] += 1
        except (BrokenPipeError, ConnectionResetError):
            state['cancel'].set()
        finally:
            limit.release()
            state['done'].set()

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
port = server.server_port

def connect(path, method='GET'):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    c.request(method, path)
    return c, c.getresponse()

try:
    start = time.perf_counter()
    conn, response = connect('/stream/cancelled')
    assert response.status == 200
    received = 0
    ttft = None
    while received < 3:
        line = response.readline()
        assert line
        if line.startswith(b'data:'):
            received += 1
            if ttft is None: ttft = time.perf_counter()-start
    other, rejected = connect('/stream/overloaded')
    assert rejected.status == 429
    other.close()
    cancel_start = time.perf_counter()
    control, accepted = connect('/cancel/cancelled', 'POST')
    assert accepted.status == 202
    control.close()
    assert runs['cancelled']['done'].wait(2)
    release_ms = (time.perf_counter()-cancel_start)*1000
    conn.close()
    assert 3 <= runs['cancelled']['generated'] < 20
    retry, conflict = connect('/stream/cancelled')
    assert conflict.status == 409
    retry.close()
    normal, full = connect('/stream/complete')
    content = full.read()
    normal.close()
    assert content.count(b'data:') == 20
    assert runs['complete']['done'].wait(2)
    assert runs['complete']['generated'] == runs['complete']['written'] == 20
    print(json.dumps(dict(python=platform.python_version(),transport='real loopback HTTP/1.0 SSE',
        first_chunk_ms=round(ttft*1000,3),cancel_release_ms=round(release_ms,3),
        cancelled_generated=runs['cancelled']['generated'],cancelled_client_received=received,
        normal_chunks=20,overload_status=429,retry_after_partial_status=409,
        billing_unit='mock generated chunk, not model token',pass_checks=True),indent=2))
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
