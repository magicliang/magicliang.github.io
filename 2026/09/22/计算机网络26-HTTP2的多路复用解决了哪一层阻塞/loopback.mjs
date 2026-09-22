#!/usr/bin/env node
// Run: node loopback.mjs. Uses only Node built-ins and a random loopback port.
import http2 from 'node:http2';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createHash } from 'node:crypto';
import os from 'node:os';

if (process.argv.includes('--help')) {
  console.log('Usage: node loopback.mjs [--help]\nBounded local HTTP/2 prior-knowledge experiment; no loss injection.');
  process.exit(0);
}
if (process.argv.length !== 2) {
  console.error('Unknown argument. Use --help.');
  process.exit(2);
}
const events = [];
const stamp = (event, fields = {}) => {
  const row = { event, monotonic_ns: process.hrtime.bigint().toString(), ...fields };
  events.push(row);
  console.log(JSON.stringify(row));
};
const slowBody = Buffer.alloc(65536, 83);
const fastBody = Buffer.from('FAST-26');
const server = http2.createServer();
const sessions = new Set();
const streams = new Map();
let client;
let pendingFast = true;
const timeout = setTimeout(() => {
  console.error('Experiment deadline exceeded');
  process.exitCode = 1;
  client?.destroy();
  for (const session of sessions) session.destroy();
  server.close();
}, 8000);
server.on('session', session => {
  sessions.add(session);
  stamp('server_session', { count: sessions.size });
});
server.on('stream', (stream, headers) => {
  const path = headers[':path'];
  assert.ok(path === '/slow' || path === '/fast');
  assert.ok(!streams.has(path));
  streams.set(path, stream);
  stamp('server_request', { path, id: stream.id, remotePort: stream.session.socket.remotePort });
  if (streams.size === 2) {
    assert.equal(sessions.size, 1);
    const slow = streams.get('/slow');
    const fast = streams.get('/fast');
    assert.notEqual(slow.id, fast.id);
    stamp('both_requests_open', { ids: [slow.id, fast.id], state: slow.session.state });
    slow.respond({ ':status': 200, 'content-length': slowBody.length, 'x-lab': 'network26' });
    slow.write(slowBody.subarray(0, 16));
    fast.respond({ ':status': 200, 'content-length': fastBody.length, 'x-lab': 'network26' });
    fast.end(fastBody);
    stamp('fast_response_queued_while_slow_open');
  }
});
try {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  stamp('environment', { node: process.version, nghttp2: process.versions.nghttp2,
    system: `${os.type()} ${os.release()} ${os.arch()}`, port: address.port,
    transport: 'cleartext prior knowledge; no TLS or fault injection' });
  client = http2.connect(`http://127.0.0.1:${address.port}`, { settings: { initialWindowSize: 1024 } });
  await once(client, 'localSettings');
  stamp('settings_acknowledged', { local: client.localSettings, remote: client.remoteSettings });
  const fetch = async path => {
    const request = client.request({ ':method': 'GET', ':path': path });
    const chunks = [];
    request.on('response', headers => assert.equal(headers[':status'], 200));
    request.on('data', chunk => chunks.push(chunk));
    request.end();
    await once(request, 'end');
    const body = Buffer.concat(chunks);
    assert.deepEqual(body, path === '/fast' ? fastBody : slowBody);
    stamp('client_complete', { path, id: request.id, bytes: body.length,
      sha256: createHash('sha256').update(body).digest('hex') });
    if (path === '/fast') {
      pendingFast = false;
      stamp('release_slow_after_fast_received');
      streams.get('/slow').end(slowBody.subarray(16));
    } else {
      assert.equal(pendingFast, false);
    }
  };
  await Promise.all([fetch('/slow'), fetch('/fast')]);
  assert.equal(events.filter(e => e.event === 'server_session').length, 1);
  assert.deepEqual(events.filter(e => e.event === 'client_complete').map(e => e.path), ['/fast', '/slow']);
  stamp('verified_local', { one_session_two_overlapping_streams: true, complete_bodies: true,
    tcp_loss: 'NOT_RUN', flow_window_exhaustion: 'not independently observed' });
  client.close();
  await once(client, 'close');
} finally {
  clearTimeout(timeout);
  client?.destroy();
  for (const session of sessions) session.destroy();
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  stamp('cleanup', { server_closed: true, sessions_destroyed: true });
}
