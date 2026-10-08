import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Export only: never sends requests or writes files.
const http = readFileSync(new URL('./mapping-lab.http', import.meta.url), 'utf8');
const coverage = JSON.parse(readFileSync(new URL('./mapping-lab-coverage.json', import.meta.url), 'utf8'));
const requests = http.split(/^### /m).slice(1).map((block) => {
  const lines = block.trim().split('\n');
  const header = lines.shift().match(/^(\S+) \[([^\]]+)\]$/);
  assert.ok(header, 'Invalid case header');
  const executable = lines.filter((line) => !line.startsWith('#') && line.trim());
  const request = executable.shift().match(/^(GET|POST|PUT) (\/\S*)$/);
  assert.ok(request, 'Invalid request line');
  return { id: header[1], group: header[2], method: request[1], path: request[2],
    body: executable.length ? JSON.parse(executable.join('\n')) : undefined };
});
assert.equal(requests.length, coverage.cases.length);
for (const [i, request] of requests.entries()) {
  for (const key of ['id', 'group', 'method', 'path']) {
    assert.equal(request[key], coverage.cases[i][key], request.id + ': stale ' + key);
  }
}
const [format, ...ids] = process.argv.slice(2);
assert.ok(['postman', 'curl'].includes(format), 'Usage: node export-mapping-lab.mjs postman [CASE ...] | curl CASE [CASE ...]');
assert.ok(format !== 'curl' || ids.length, 'curl export requires explicit case IDs');
for (const id of ids) assert.ok(requests.some((r) => r.id === id), 'Unknown case: ' + id);
const selected = ids.length ? ids.map((id) => requests.find((r) => r.id === id)) : requests;
if (format === 'postman') {
  const item = Object.entries(coverage.groups).map(([group, details]) => ({
    name: group,
    description: details.prerequisites,
    item: selected.filter((r) => r.group === group).map((r) => {
      const parsed = new URL(r.path, 'http://localhost');
      const request = {
        method: r.method,
        header: r.body === undefined ? [] : [{ key: 'Content-Type', value: 'application/json' }],
        url: { raw: '{{baseUrl}}' + r.path, host: ['{{baseUrl}}'],
          path: parsed.pathname.split('/').filter(Boolean),
          query: [...parsed.searchParams].map(([key, value]) => ({ key, value })) },
        description: details.prerequisites + '\nExpected (NOT_RUN): ' + coverage.cases.find((c) => c.id === r.id).expected,
      };
      if (r.body !== undefined) request.body = { mode: 'raw', raw: JSON.stringify(r.body, null, 2),
        options: { raw: { language: 'json' } } };
      return { name: r.id, request };
    }),
  })).filter((folder) => folder.item.length);
  console.log(JSON.stringify({
    info: { name: 'Elasticsearch mapping laboratory 2026-10-08',
      description: 'NOT_RUN. Execute individual requests after checking prerequisites, not the whole collection.',
      schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json' },
    variable: [{ key: 'baseUrl', value: 'http://localhost:9200', type: 'string' }],
    item,
  }, null, 2));
} else {
  const quote = (value) => "'" + value.replaceAll("'", "'\\''") + "'";
  for (const r of selected) {
    console.log('# ' + r.id + ' [' + r.group + '] NOT_RUN\n# ' + coverage.groups[r.group].prerequisites);
    let command = 'curl --fail-with-body --request ' + r.method + ' "$' + '{ES_URL:-http://localhost:9200}' + r.path + '"';
    if (r.body !== undefined) command += " --header 'Content-Type: application/json' --data-binary " + quote(JSON.stringify(r.body));
    console.log(command);
  }
}
