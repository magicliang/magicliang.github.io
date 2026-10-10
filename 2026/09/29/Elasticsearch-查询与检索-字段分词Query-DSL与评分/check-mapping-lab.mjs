import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// Static checks only: this script never connects to Elasticsearch.
const http = readFileSync(new URL('./mapping-lab.http', import.meta.url), 'utf8');
const coverage = JSON.parse(readFileSync(new URL('./mapping-lab-coverage.json', import.meta.url), 'utf8'));
const requests = http.split(/^### /m).slice(1).map((block) => {
  const lines = block.trim().split('\n');
  const header = lines.shift().match(/^(\S+) \[([^\]]+)\]$/);
  assert.ok(header, 'Each request needs a unique case ID and group');
  const expected = lines.find((line) => line.startsWith('# expected: '))?.slice(12);
  const executable = lines.filter((line) => !line.startsWith('#') && line.trim());
  const request = executable.shift().match(/^(GET|POST|PUT) (\/\S*)$/);
  assert.ok(request, `${header[1]}: invalid relative request path`);
  return {
    id: header[1], group: header[2], method: request[1], path: request[2], expected,
    body: executable.length ? JSON.parse(executable.join('\n')) : undefined,
  };
});

assert.equal(new Set(requests.map((r) => r.id)).size, requests.length, 'Duplicate case IDs');
assert.equal(requests.length, coverage.cases.length, 'Request/coverage count mismatch');
const types = {};
function collect(properties, prefix, group) {
  for (const [name, field] of Object.entries(properties ?? {})) {
    const path = prefix ? `${prefix}.${name}` : name;
    if (field.type) (types[field.type] ??= []).push({ field: path, group });
    collect(field.properties, path, group);
    collect(field.fields, path, group);
  }
}
for (const [i, request] of requests.entries()) {
  const recorded = coverage.cases[i];
  for (const key of ['id', 'group', 'method', 'path', 'expected']) {
    assert.equal(request[key], recorded[key], `${request.id}: stale ${key}`);
  }
  assert.ok(coverage.groups[request.group], `${request.id}: missing prerequisites`);
  if (request.body?.mappings) collect(request.body.mappings.properties, '', request.group);
}
assert.deepEqual(types, coverage.types, 'Stale field-type coverage');
assert.equal(coverage.all_combinations, false, 'Do not claim exhaustive parameter combinations');

const main = requests.find((r) => r.id === 'SETUP01').body;
const docs = requests.filter((r) => /^DOC0[123]$/.test(r.id));
assert.equal(docs.length, 3);
for (const document of docs) {
  for (const field of Object.keys(document.body)) {
    assert.ok(main.mappings.properties[field], `${document.id}: undefined top-level field ${field}`);
  }
}
assert.equal(main.mappings.properties.embedding.dims, 3);
for (const document of docs) {
  assert.equal(document.body.embedding.length, 3);
  assert.ok(document.body.embedding.some((v) => v !== 0), 'Cosine vectors must be nonzero');
}
assert.equal(docs[0].body.u64, '18446744073709551615', 'Do not round unsigned_long via a JS number');
assert.equal(docs[0].body.users[0].role, 'reader');
assert.equal(docs[0].body.users[1].name, 'Bob');
assert.equal(main.mappings.properties.id_alias.path, 'id');
assert.equal(main.mappings.properties.title.copy_to, 'all_text');
assert.equal(main.mappings.properties.users.type, 'nested');
assert.equal(main.mappings.properties.users_object.type, 'object');
assert.equal(main.mappings.properties.source_only.index, false);
assert.equal(main.mappings.properties.source_only.doc_values, false);
assert.equal(main.mappings.properties.no_positions.index_options, 'freqs');
assert.equal(docs[0].body.latency_hist.values.length, docs[0].body.latency_hist.counts.length);
assert.equal(docs[0].body.latency_metrics.sum / docs[0].body.latency_metrics.value_count, 16);

const exporter = fileURLToPath(new URL('./export-mapping-lab.mjs', import.meta.url));
const postman = JSON.parse(execFileSync(process.execPath, [exporter, 'postman'], { encoding: 'utf8' }));
const savedPostman = JSON.parse(readFileSync(new URL('./mapping-lab.postman_collection.json', import.meta.url), 'utf8'));
assert.deepEqual(postman, savedPostman, 'Regenerate the Postman collection');
const exported = postman.item.flatMap((folder) => folder.item);
assert.equal(exported.length, requests.length);
for (const r of requests) {
  const p = exported.find((item) => item.name === r.id).request;
  assert.equal(p.method, r.method);
  assert.equal(p.url.raw, '{{baseUrl}}' + r.path);
  assert.deepEqual(p.body ? JSON.parse(p.body.raw) : undefined, r.body);
}
const curl = execFileSync(process.execPath, [exporter, 'curl', 'Q01'], { encoding: 'utf8' });
// Replace curl with an argument recorder: validate shell quoting without network access.
const shell = execFileSync('bash', ['-c', 'curl(){ printf \'%s\\0\' "$@"; }\n' + curl], {
  encoding: 'utf8', env: { ...process.env, ES_URL: 'https://example.invalid:9200' },
}).split('\0');
assert.equal(shell[shell.indexOf('--request') + 1], 'POST');
assert.ok(shell.includes('https://example.invalid:9200/es-query-lab-v1/_search'));
assert.deepEqual(JSON.parse(shell[shell.indexOf('--data-binary') + 1]), requests.find((r) => r.id === 'Q01').body);
assert.notEqual(spawnSync(process.execPath, [exporter, 'curl']).status, 0);
assert.notEqual(spawnSync(process.execPath, [exporter, 'curl', 'UNKNOWN']).status, 0);

console.log(`PASS: ${requests.length} requests; ${Object.keys(types).length} named field types; 3 core documents; Postman parity; curl quoting`);
console.log(`Server execution status: ${coverage.execution_status}. JSON validity is not ES compatibility.`);
