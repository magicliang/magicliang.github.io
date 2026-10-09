#!/usr/bin/env python3
"""Disposable loopback-only ES cluster and runner; Python standard library only."""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

VERSIONS = 'https://artifacts-api.elastic.co/v1/versions'
IMAGE = 'docker.elastic.co/elasticsearch/elasticsearch'
CLUSTER = 'es-http-tutorial'
LABEL = 'io.es-tutorial.owner'


def latest(versions):
    stable = [v for v in versions if re.fullmatch(r'\d+\.\d+\.\d+', v)]
    if not stable:
        raise ValueError('Official API returned no stable semantic versions')
    return max(stable, key=lambda v: tuple(map(int, v.split('.'))))


def http(base, method='GET', path='/', body=None):
    data = None if body is None else json.dumps(body).encode()
    request = Request(base.rstrip('/') + path, data=data, method=method,
                      headers={'Content-Type': 'application/json'})
    try:
        response = urlopen(request, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read().decode()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = raw
        return response.status if hasattr(response, 'status') else response.code, result


def local_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or
            parsed.username or parsed.password or parsed.path not in ('', '/') or
            parsed.query or parsed.fragment or not parsed.port):
        raise ValueError('Use http://127.0.0.1:PORT for this unauthenticated lab')
    return value.rstrip('/')


def command(engine, *args, capture=False):
    return subprocess.run([engine, *args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def config(node, names, bootstrap=True):
    values = {'cluster.name': CLUSTER, 'node.name': node, 'network.host': '0.0.0.0',
              'discovery.seed_hosts': names, 'xpack.security.enabled': False,
              'xpack.security.autoconfiguration.enabled': False,
              'xpack.security.http.ssl.enabled': False,
              'xpack.security.transport.ssl.enabled': False,
              'xpack.ml.enabled': False,
              'node.roles': ['master', 'data', 'ingest', 'remote_cluster_client']}
    if bootstrap:
        values['cluster.initial_master_nodes'] = names
    return ''.join(key + ': ' + json.dumps(value) + '\n' for key, value in values.items())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def up(args):
    engine = args.engine or ('docker' if shutil.which('docker') else 'podman')
    command(engine, 'info', capture=True)
    if args.version:
        if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
            raise ValueError('--version must be a stable X.Y.Z')
        version = args.version
    else:
        status, versions = http('https://artifacts-api.elastic.co', path='/v1/versions')
        if status != 200:
            raise ValueError('Official version API failed; no cached fallback')
        version = latest(versions['versions'])
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    owner = uuid.uuid4().hex
    network = 'eslab-' + owner[:12]
    names = [network + '-es0' + str(i) for i in range(1, 4)]
    state = {'engine': engine, 'owner': owner, 'network': network, 'containers': names,
             'version': version, 'image': IMAGE + ':' + version,
             'base_url': 'http://127.0.0.1:' + str(args.port), 'status': 'PREPARING',
             'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    save(work / 'state.json', state)
    command(engine, 'pull', state['image'])  # Always pull, including pinned versions.
    state['image_inspect'] = json.loads(command(engine, 'image', 'inspect', state['image'], capture=True))
    save(work / 'state.json', state)
    command(engine, 'network', 'create', '--label', LABEL + '=' + owner, network)
    for i, name in enumerate(names):
        cfg = work / (name + '.yml')
        cfg.write_text(config(name, names))
        cfg.chmod(0o644)
        options = ['run', '-d', '--name', name, '--network', network,
                   '--label', LABEL + '=' + owner, '--memory', '2g',
                   '--ulimit', 'nofile=65535:65535',
                   '-e', 'ES_JAVA_OPTS=-Xms1g -Xmx1g',
                   '-v', str(cfg) + ':/usr/share/elasticsearch/config/elasticsearch.yml:ro,Z']
        if i == 0:
            options += ['-p', '127.0.0.1:' + str(args.port) + ':9200']
        command(engine, *options, state['image'])
    deadline = time.monotonic() + args.wait
    while time.monotonic() < deadline:
        try:
            status, health = http(state['base_url'], path='/_cluster/health?wait_for_nodes=3&wait_for_status=green&timeout=5s')
            if status == 200 and not health.get('timed_out') and health.get('number_of_nodes') == 3 and health.get('status') == 'green':
                break
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2)
    else:
        raise TimeoutError('Cluster not ready. Inspect container logs; state.json retained for scoped cleanup')
    status, root = http(state['base_url'])
    if status != 200 or root['version']['number'] != version or root['cluster_name'] != CLUSTER:
        raise ValueError('Unexpected cluster identity/version')
    # In-place writes retain the bind-mounted inode. Bootstrap is removed before any restart.
    for name in names:
        (work / (name + '.yml')).write_text(config(name, names, bootstrap=False))
    state.update(status='READY', server=root, health=health)
    save(work / 'state.json', state)
    print('READY ' + state['base_url'] + ' version=' + version)


def down(args):
    work = args.workdir.resolve()
    state = json.loads((work / 'state.json').read_text())
    if state['status'] == 'REMOVED':
        print('Already removed; evidence retained')
        return
    engine = state['engine']
    if not args.discard_data:
        raise ValueError('down requires --discard-data: container data is disposable')
    targets = [('container', name) for name in state['containers']] + [('network', state['network'])]
    # Validate ownership of every existing target before deleting any of them.
    existing = []
    for kind, name in targets:
        result = subprocess.run([engine, kind, 'inspect', name], text=True, capture_output=True)
        if result.returncode:
            if 'no such' in result.stderr.lower() or 'not found' in result.stderr.lower():
                continue
            raise RuntimeError(result.stderr)
        info = json.loads(result.stdout)[0]
        labels = info.get('Labels', info.get('labels', {})) if kind == 'network' else info['Config'].get('Labels', {})
        if labels.get(LABEL) != state['owner']:
            raise ValueError('Refuse unrelated resource: ' + name)
        existing.append((kind, name))
    for kind, name in existing:
        if kind == 'container':
            command(engine, 'rm', '-f', '-v', name)
        else:
            command(engine, 'network', 'rm', name)
    state['status'] = 'REMOVED'
    save(work / 'state.json', state)
    print('Removed owned containers/anonymous data volumes/network; evidence retained')


def parse_requests(text):
    requests = []
    for block in re.split(r'^### ', text, flags=re.M)[1:]:
        lines = block.strip().splitlines()
        match = re.fullmatch(r'(\S+) \[([^\]]+)\]', lines.pop(0))
        if not match:
            raise ValueError('Invalid experiment header')
        expected = next((line[12:] for line in lines if line.startswith('# expected: ')), '')
        executable = [line for line in lines if line.strip() and not line.startswith('#')]
        method, path = executable.pop(0).split(' ', 1)
        if method not in ('GET', 'POST', 'PUT') or not path.startswith('/') or path.startswith('//'):
            raise ValueError('Unsupported experiment request')
        requests.append({'id': match[1], 'group': match[2], 'method': method, 'path': path,
                         'expected': expected, 'body': json.loads('\n'.join(executable)) if executable else None})
    if not requests or len({r['id'] for r in requests}) != len(requests):
        raise ValueError('Missing or duplicate experiment IDs')
    return requests


def run(args):
    base = local_url(args.base_url)
    status, root = http(base)
    if status != 200 or root.get('cluster_name') != CLUSTER:
        raise ValueError('Refuse writes: endpoint is not es-http-tutorial')
    requests = parse_requests(args.http.read_text())
    if args.case:
        by_id = {r['id']: r for r in requests}
        requests = [by_id[key] for key in args.case]  # Unknown IDs fail before writes.
    else:
        groups = args.group or ['environment', 'core']
        unknown = set(groups) - {r['group'] for r in requests}
        if unknown:
            raise ValueError('Unknown groups: ' + str(unknown))
        requests = [r for r in requests if r['group'] in groups]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'server': root, 'source': str(args.http.resolve()), 'cases': [],
              'started_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    checks = {'Q01': {'1', '2'}, 'Q02': {'1'}, 'Q03': {'1'}, 'Q05': set(), 'Q06': {'1'}}
    failures = 0
    for r in requests:
        try:
            status, result = http(base, r['method'], r['path'], r['body'])
            negative = r['group'] == 'negative'
            ok = 400 <= status < 500 if negative else 200 <= status < 300
            verdict = 'EXPECTED_HTTP_ERROR' if negative and ok else 'HTTP_OK' if ok else 'FAIL'
            if ok and r['id'] in checks:
                hits = result['hits']
                ids = {hit['_id'] for hit in hits['hits']}
                ok = ids == checks[r['id']] and hits['total']['value'] == len(ids)
                verdict = 'PASS_HITS' if ok else 'FAIL_HITS'
            entry = {**r, 'http_status': status, 'observed': result, 'status': verdict}
        except (URLError, TimeoutError, ConnectionError) as error:
            ok = False
            entry = {**r, 'status': 'TRANSPORT_ERROR', 'error': str(error)}
        failures += not ok
        report['cases'].append(entry)
        save(output / 'results.json', report)
        print(r['id'] + ' ' + entry['status'])
        if not ok and (r['id'].startswith('SETUP') or r['id'].startswith('DOC')):
            break  # Do not run queries after setup/ingestion failure.
    if failures:
        raise RuntimeError(str(failures) + ' failures; inspect ' + str(output / 'results.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    start = sub.add_parser('up')
    start.add_argument('--engine', choices=['docker', 'podman'])
    start.add_argument('--version')
    start.add_argument('--port', type=int, default=19200)
    start.add_argument('--wait', type=int, default=240)
    for action in (start, sub.add_parser('down')):
        action.add_argument('--workdir', type=Path, default=Path('.es-http-lab'))
    sub.choices['down'].add_argument('--discard-data', action='store_true')
    execute = sub.add_parser('run')
    execute.add_argument('--base-url', default='http://127.0.0.1:19200')
    execute.add_argument('--http', type=Path, required=True)
    execute.add_argument('--output', type=Path, required=True)
    execute.add_argument('--group', action='append')
    execute.add_argument('--case', action='append')
    args = parser.parse_args()
    if args.action == 'up' and (not 1 <= args.port <= 65535 or args.wait <= 0):
        parser.error('Invalid port/wait')
    if args.action == 'run' and args.case and args.group:
        parser.error('Choose --case or --group, not both')
    {'up': up, 'down': down, 'run': run}[args.action](args)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
