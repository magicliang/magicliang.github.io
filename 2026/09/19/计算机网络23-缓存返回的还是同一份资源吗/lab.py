#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 lab.py; --self-check performs offline age checks only
"""Two loopback HTTP services: controlled origin and deliberately limited teaching cache."""
import argparse
import http.client
import http.server
import json
import platform
import re
import threading
import time
from contextlib import closing
from dataclasses import asdict, dataclass, field
from email.utils import formatdate, parsedate_to_datetime


class CacheError(Exception):
    """Origin response is outside the experiment's fixed contract."""


@dataclass(frozen=True, slots=True)
class AgeInputs:
    date_wall: float
    age_value: float
    request_mono: float
    response_mono: float
    response_wall: float

    def current(self, now_mono: float) -> float:
        apparent = max(0, self.response_wall - self.date_wall)
        corrected = self.age_value + self.response_mono - self.request_mono
        return max(apparent, corrected) + now_mono - self.response_mono


@dataclass(frozen=True, slots=True)
class Entry:
    headers: tuple[tuple[str, str], ...]
    body: bytes
    age: AgeInputs


def fresh(entry: Entry, now: float) -> bool:
    control = dict(entry.headers)['cache-control']
    if 'no-cache' in [part.strip() for part in control.split(',')]: return False
    match = re.search(r'(?:^|,)\s*max-age=([0-9]+)(?:,|$)', control)
    if match is None: raise CacheError('explicit max-age required')
    return int(match[1]) > entry.age.current(now)


@dataclass(frozen=True, slots=True)
class State:
    """Mutable test state; each service is serial and driver changes version between requests."""
    version: list[int] = field(default_factory=lambda: [1])
    entries: dict[tuple[str, str | None], Entry] = field(default_factory=dict)
    origin_log: list = field(default_factory=list)
    decisions: list = field(default_factory=list)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def setup(self) -> None:
        super().setup(); self.connection.settimeout(3)

    def log_message(self, format: str, *args: str) -> None:
        return

    def emit(self, status: int, entry: Entry) -> None:
        self.send_response_only(status)
        for key, value in entry.headers:
            if key not in ('content-length', 'connection'): self.send_header(key, value)
        if status != 304: self.send_header('content-length', str(len(entry.body)))
        self.send_header('connection', 'close'); self.end_headers()
        if status != 304: self.wfile.write(entry.body)
        self.close_connection = True


def origin_handler(state: State) -> type[Handler]:
    class Origin(Handler):
        def do_GET(self) -> None:
            language = self.headers.get('Accept-Language')
            if self.path not in ('/cache', '/no-cache', '/no-store') or language not in (None, 'zh', 'en'):
                self.send_error(400); return
            variant = 'missing' if language is None else language
            text = {'zh': '你好', 'en': 'hello', 'missing': 'default'}[variant]
            body = f'{text} v{state.version[0]}'.encode()
            etag = f'"{self.path[1:]}-{variant}-v{state.version[0]}"'
            status = 304 if self.headers.get('If-None-Match') == etag else 200
            control = {'/cache': 'max-age=2', '/no-cache': 'max-age=30, no-cache', '/no-store': 'max-age=30, no-store'}[self.path]
            headers = (('date', formatdate(usegmt=True)), ('cache-control', control), ('vary', 'Accept-Language'),
                       ('etag', etag), ('age', '0'), ('content-type', 'text/plain; charset=utf-8'))
            actual = b'' if status == 304 else body
            state.origin_log.append({'path': self.path, 'request_headers': list(self.headers.items()),
                                     'status': status, 'headers': headers, 'body_hex': actual.hex(), 'time_mono': time.monotonic()})
            self.emit(status, Entry(headers, actual, AgeInputs(0, 0, 0, 0, 0)))
    return Origin


def fetch(port: int, path: str, headers: dict[str, str]) -> tuple[int, Entry]:
    before = time.monotonic()
    with closing(http.client.HTTPConnection('127.0.0.1', port, timeout=3)) as connection:
        connection.request('GET', path, headers=headers)
        response = connection.getresponse(); body = response.read(65537)
        received, wall = time.monotonic(), time.time()
        if len(body) > 65536: raise CacheError('body limit')
        metadata = tuple((key.lower(), value) for key, value in response.getheaders())
        values = dict(metadata)
        age = AgeInputs(parsedate_to_datetime(values['date']).timestamp(), float(values.get('age', '0')), before, received, wall)
        return response.status, Entry(metadata, body, age)


def validated(previous: Entry, upstream: Entry) -> Entry:
    if dict(previous.headers)['etag'] != dict(upstream.headers).get('etag'):
        raise CacheError('304 does not identify stored ETag')
    if upstream.body: raise CacheError('304 body outside contract')
    merged = {**dict(previous.headers), **dict(upstream.headers)}
    return Entry(tuple(merged.items()), previous.body, upstream.age)


def cache_handler(state: State, origin_port: int) -> type[Handler]:
    class Cache(Handler):
        def do_GET(self) -> None:
            language = self.headers.get('Accept-Language')
            if self.path not in ('/cache', '/no-cache', '/no-store') or language not in (None, 'zh', 'en') or self.headers.get('If-None-Match'):
                self.send_error(400); return
            key = (self.path, language)
            old = state.entries.get(key)
            before_count = len(state.origin_log)
            now = time.monotonic(); previous_age = old.age.current(now) if old else None
            upstream_record = None
            if old is not None and fresh(old, now):
                entry, decision = old, 'fresh-hit'
            else:
                request_headers = {} if language is None else {'Accept-Language': language}
                if old is not None: request_headers['If-None-Match'] = dict(old.headers)['etag']
                status, incoming = fetch(origin_port, self.path, request_headers)
                upstream_record = {'status': status, 'headers': incoming.headers, 'body_hex': incoming.body.hex(), 'request_headers': request_headers}
                if dict(incoming.headers).get('vary') != 'Accept-Language': raise CacheError('Vary outside fixed contract')
                if status == 304:
                    if old is None: raise CacheError('304 without stored representation')
                    entry, decision = validated(old, incoming), 'validated-304'
                elif status == 200: entry, decision = incoming, 'origin-200'
                else: raise CacheError('origin status outside contract')
                if 'no-store' not in [part.strip() for part in dict(entry.headers)['cache-control'].split(',')]: state.entries[key] = entry
                else: state.entries.pop(key, None); decision = 'no-store-200'
            age_now = time.monotonic(); current_age = entry.age.current(age_now)
            output_headers = {**dict(entry.headers), 'age': str(int(current_age))}
            state.decisions.append({'key': key, 'request_headers': list(self.headers.items()), 'decision': decision,
                'origin_before': before_count, 'origin_after': len(state.origin_log), 'age_before': previous_age,
                'age_inputs': asdict(entry.age), 'age_now_mono': age_now, 'current_age': current_age,
                'upstream': upstream_record, 'stored': key in state.entries, 'downstream_status': 200,
                'downstream_headers': list(output_headers.items()), 'downstream_body_hex': entry.body.hex()})
            self.emit(200, Entry(tuple(output_headers.items()), entry.body, entry.age))
    return Cache


def self_check() -> None:
    age = AgeInputs(100, 3, 10, 10.5, 102)
    assert age.current(12) == 5
    apparent = AgeInputs(100, 0, 10, 10.5, 102)
    assert apparent.current(12) == 3.5
    entry = Entry((('cache-control', 'max-age=5'), ('etag', '"v1"')), b'body', age)
    assert fresh(entry, 11.999) and not fresh(entry, 12)
    refreshed = validated(entry, Entry((('etag', '"v1"'), ('date', 'new'), ('cache-control', 'max-age=2')), b'', apparent))
    assert refreshed.body == b'body' and dict(refreshed.headers)['date'] == 'new'
    try: validated(entry, Entry((('etag', '"v2"'),), b'', apparent))
    except CacheError: rejected = True
    else: rejected = False
    assert rejected
    print(json.dumps({'verification': 'offline-age-and-304', 'corrected_age': 5, 'apparent_age_case': 3.5,
                      'equal_max_age_is_stale': True, 'mismatched_304_rejected': rejected}))


def lab() -> None:
    state = State()
    with http.server.HTTPServer(('127.0.0.1', 0), origin_handler(state)) as origin:
        with http.server.HTTPServer(('127.0.0.1', 0), cache_handler(state, origin.server_port)) as cache:
            threads = [threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}) for server in (origin, cache)]
            for thread in threads: thread.start()
            try:
                print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(), 'origin': origin.server_address, 'cache': cache.server_address}), flush=True)
                cases = [('cold', '/cache', 'zh', 1), ('fresh', '/cache', 'zh', 0), ('expired-304', '/cache', 'zh', 1),
                         ('modified-200', '/cache', 'zh', 1), ('en-cold', '/cache', 'en', 1), ('missing-cold', '/cache', None, 1),
                         ('en-hit', '/cache', 'en', 0), ('missing-hit', '/cache', None, 0), ('zh-hit', '/cache', 'zh', 0),
                         ('no-cache-first', '/no-cache', 'zh', 1), ('no-cache-again', '/no-cache', 'zh', 1),
                         ('no-store-first', '/no-store', 'zh', 1), ('no-store-again', '/no-store', 'zh', 1)]
                bodies = {}
                for label, path, language, delta in cases:
                    if label == 'modified-200': state.version[0] = 2
                    if label in ('expired-304', 'modified-200'):
                        target = state.entries[(path, language)].age.response_mono + 3.1
                        time.sleep(max(0, target - time.monotonic()))
                    before = len(state.origin_log)
                    status, reply = fetch(cache.server_port, path, {} if language is None else {'Accept-Language': language})
                    assert status == 200 and len(state.origin_log) - before == delta
                    event = state.decisions[-1]
                    if label == 'expired-304': assert event['upstream']['status'] == 304 and reply.body == bodies['cold']
                    if label == 'modified-200': assert event['upstream']['status'] == 200 and reply.body != bodies['cold']
                    if label == 'fresh': assert dict(reply.headers)['date'] == dict(state.entries[(path, language)].headers)['date']
                    if label == 'no-cache-again': assert event['upstream']['status'] == 304 and event['stored']
                    if label.startswith('no-store'): assert event['upstream']['status'] == 200 and not event['stored']
                    bodies[label] = reply.body
                    print(json.dumps({'case': label, 'client_status': status, 'client_headers': reply.headers, 'client_body_hex': reply.body.hex(), 'cache_event': event}), flush=True)
                assert bodies['en-cold'] != bodies['missing-cold'] != bodies['modified-200']
                assert bodies['en-cold'] == bodies['en-hit'] and bodies['missing-cold'] == bodies['missing-hit']
            finally:
                for server in (cache, origin): server.shutdown()
                for thread in threads: thread.join(timeout=4)
                assert not any(thread.is_alive() for thread in threads)
                print(json.dumps({'origin_requests': state.origin_log, 'origin_count': len(state.origin_log), 'owned_threads_stopped': True}), flush=True)
    print(json.dumps({'owned_servers_closed': True}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    self_check()
    if not args.self_check: lab()


if __name__ == '__main__': main()
