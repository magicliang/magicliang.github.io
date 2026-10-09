import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import es_lab as lab


class LabTest(unittest.TestCase):
    def test_latest(self):
        self.assertEqual(lab.latest(['9.9.0', '9.10.0', '10.0.0-rc1', '10.0.0-SNAPSHOT']), '9.10.0')
        with self.assertRaises(ValueError):
            lab.latest(['latest', '9.6.0-SNAPSHOT'])

    def test_loopback_and_parser(self):
        for value in ['http://example.com:9200', 'https://127.0.0.1:9200', 'http://127.0.0.1:9200/path']:
            with self.assertRaises(ValueError):
                lab.local_url(value)
        self.assertEqual(lab.local_url('http://127.0.0.1:19200'), 'http://127.0.0.1:19200')
        sample = '### Q01 [core]\n# expected: quoted\nGET /_search\n{"query":{"match":{"title":"don\'t have"}}}\n'
        self.assertEqual(lab.parse_requests(sample)[0]['body']['query']['match']['title'], "don't have")
        with self.assertRaises(ValueError):
            lab.parse_requests(sample + sample)
        with self.assertRaises(ValueError):
            lab.parse_requests(sample.replace('GET /_search', 'POST //external'))

    def test_up_always_pulls_and_removes_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'lab'
            args = argparse.Namespace(engine='podman', version=None, workdir=work, port=19200, wait=10)
            def response(base, method='GET', path='/', body=None):
                if path == '/v1/versions':
                    return 200, {'versions': ['9.5.4', '9.5.5', '9.6.0-SNAPSHOT']}
                if path.startswith('/_cluster/health'):
                    return 200, {'number_of_nodes': 3, 'status': 'green', 'timed_out': False}
                return 200, {'cluster_name': lab.CLUSTER, 'version': {'number': '9.5.5'}}
            with patch.object(lab, 'http', side_effect=response), patch.object(lab, 'command', return_value='[]') as cmd:
                lab.up(args)
                self.assertIn(unittest.mock.call('podman', 'pull', lab.IMAGE + ':9.5.5'), cmd.call_args_list)
                launches = [c.args for c in cmd.call_args_list if c.args[1] == 'run']
                self.assertEqual(len(launches), 3)
                self.assertIn('127.0.0.1:19200:9200', launches[0])
                self.assertNotIn('-p', launches[1])
                self.assertTrue(all('2g' in call for call in launches))
            for cfg in work.glob('*.yml'):
                self.assertNotIn('initial_master_nodes', cfg.read_text())
                self.assertIn('xpack.security.enabled: false', cfg.read_text())
            self.assertEqual(json.loads((work / 'state.json').read_text())['status'], 'READY')

    def test_down_refuses_foreign_owner_before_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            lab.save(work / 'state.json', {'engine': 'podman', 'owner': 'owned', 'containers': ['es01'],
                                          'network': 'net', 'status': 'READY'})
            args = argparse.Namespace(workdir=work, discard_data=True)
            result = argparse.Namespace(returncode=0, stderr='', stdout='[{"Config":{"Labels":{}}}]')
            with patch.object(lab.subprocess, 'run', return_value=result), patch.object(lab, 'command') as command:
                with self.assertRaises(ValueError):
                    lab.down(args)
                command.assert_not_called()

    def test_setup_failure_stops_queries_and_keeps_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lab.http'
            path.write_text('### SETUP01 [core]\nPUT /lab\n{}\n\n### Q01 [core]\nPOST /lab/_search\n{}')
            args = argparse.Namespace(base_url='http://127.0.0.1:19200', http=path,
                                      output=Path(tmp) / 'results', case=None, group=['core'])
            with patch.object(lab, 'http', side_effect=[(200, {'cluster_name': lab.CLUSTER}),
                                                      (400, {'error': 'mapping rejected'})]) as http:
                with self.assertRaises(RuntimeError):
                    lab.run(args)
                self.assertEqual(http.call_count, 2)
            report = json.loads((args.output / 'results.json').read_text())
            self.assertEqual(len(report['cases']), 1)
            self.assertEqual(report['cases'][0]['observed']['error'], 'mapping rejected')

    def test_canonical_attachment(self):
        folder = Path(__file__).resolve().parent
        path = folder / 'mapping-lab.http'
        if not path.exists():
            path = folder.parent / '2026-09-29-Elasticsearch-查询为什么没命中-从字段能力到分词短语与评分' / 'mapping-lab.http'
        requests = lab.parse_requests(path.read_text())
        self.assertEqual(len(requests), 137)
        self.assertEqual(sum(r['group'] in ('environment', 'core') for r in requests), 99)

    def test_runner_against_mock_http_server(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.reply({'cluster_name': lab.CLUSTER, 'version': {'number': 'test'}})
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append(body)
                self.reply({'hits': {'total': {'value': 2}, 'hits': [{'_id': '1'}, {'_id': '2'}]}})
            def reply(self, value):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(value).encode())
        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / 'lab.http'
                    path.write_text('### Q01 [core]\n# expected: hits 1,2\nPOST /_search\n{"query":{"match":{"title":"don\'t have"}}}')
                    args = argparse.Namespace(base_url='http://127.0.0.1:' + str(server.server_port),
                                              http=path, output=Path(tmp) / 'results', case=None, group=['core'])
                    lab.run(args)
                    report = json.loads((args.output / 'results.json').read_text())
                    self.assertEqual(report['cases'][0]['status'], 'PASS_HITS')
                    self.assertEqual(received[0]['query']['match']['title'], "don't have")
            finally:
                server.shutdown()
                thread.join()


if __name__ == '__main__':
    unittest.main()
