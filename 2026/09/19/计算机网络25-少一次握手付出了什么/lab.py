#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
# How to run: python3 lab.py; --self-check is offline only.
"""Bounded OpenSSL loopback TLS resumption and early-data experiment."""
import argparse
import json
import platform
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Final

OPENSSL: Final = '/opt/homebrew/bin/openssl'


def command(directory: Path, args: list[str]) -> str:
    result = subprocess.run([OPENSSL, *args], cwd=directory, capture_output=True, text=True, timeout=20, check=True)
    print(json.dumps({'openssl_command': args, 'stdout': result.stdout, 'stderr': result.stderr}), flush=True)
    return result.stdout


def certificates(directory: Path) -> None:
    for name in ('root', 'other'):
        command(directory, ['req', '-x509', '-newkey', 'rsa:2048', '-noenc', '-days', '1',
            '-keyout', name+'.key', '-out', name+'.pem', '-subj', '/CN=TLS Lab '+name,
            '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
            '-addext', 'keyUsage=critical,keyCertSign,cRLSign', '-addext', 'subjectKeyIdentifier=hash'])
    command(directory, ['req', '-new', '-newkey', 'rsa:2048', '-noenc', '-keyout', 'leaf.key',
        '-out', 'leaf.csr', '-subj', '/CN=unused-common-name.lab.test'])
    (directory/'leaf.ext').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\nsubjectAltName=DNS:server.lab.test\n')
    command(directory, ['x509', '-req', '-in', 'leaf.csr', '-CA', 'root.pem', '-CAkey', 'root.key',
        '-set_serial', '24', '-days', '1', '-extfile', 'leaf.ext', '-out', 'leaf.pem'])
    command(directory, ['x509', '-in', 'leaf.pem', '-noout', '-text', '-fingerprint', '-sha256'])



def public_lines(raw: str) -> list[str]:
    """Allowlist summaries only; raw session, ticket, PSK, key material stay temporary."""
    patterns = ('New, TLSv1.3', 'Reused, TLSv1.3', 'Early data was', 'Early data received:',
                'No early data received', 'End of early data', 'LAB25-EARLY-SAFE',
                'Verification: OK', 'Verified peername:', 'Verify return code:', 'CONNECTION ESTABLISHED')
    return [line.strip() for line in raw.splitlines() if line.strip().startswith(patterns)]


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)


def self_check() -> None:
    selected = public_lines('Resumption PSK: SECRET\nNew, TLSv1.3, Cipher is TEST\nSSL SESSION PARAMETERS\nEarly data was accepted')
    assert len(selected) == 2 and all('SECRET' not in line for line in selected)
    print(json.dumps({'offline_self_check': 'summary allowlist excludes synthetic secret'}))


def lab() -> None:
    with tempfile.TemporaryDirectory(prefix='network25-') as temporary:
        directory = Path(temporary)
        command(directory, ['version']); certificates(directory)
        (directory/'early.txt').write_text('LAB25-EARLY-SAFE\n')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
        server_args = [OPENSSL, 's_server', '-accept', f'127.0.0.1:{port}', '-cert', 'leaf.pem',
            '-key', 'leaf.key', '-tls1_3', '-early_data', '-max_early_data', '1024',
            '-recv_max_early_data', '1024', '-anti_replay', '-num_tickets', '2', '-naccept', '3']
        print(json.dumps({'environment': platform.platform(), 'server_command': server_args,
            'anti_replay': 'explicit -anti_replay; never disabled', 'secret_logs': 'temporary only; published summaries allowlisted'}), flush=True)
        with (directory/'server.log').open('w+') as server_log:
            with subprocess.Popen(server_args, cwd=directory, stdin=subprocess.PIPE, stdout=server_log, stderr=subprocess.STDOUT, text=True) as server:
                try:
                    deadline = time.monotonic()+5
                    while 'ACCEPT' not in (directory/'server.log').read_text():
                        if server.poll() is not None or time.monotonic() >= deadline: raise TimeoutError('server readiness')
                        time.sleep(.02)
                    for index in range(3):
                        args = [OPENSSL, 's_client', '-connect', f'127.0.0.1:{port}', '-servername', 'server.lab.test',
                            '-verify_hostname', 'server.lab.test', '-verify_return_error', '-CAfile', 'root.pem',
                            '-no-CApath', '-no-CAstore', '-tls1_3', '-no_ign_eof', '-sess_out', f'session{index}.pem']
                        if index > 0: args += ['-sess_in', f'session{index-1}.pem']
                        if index == 2: args += ['-early_data', 'early.txt']
                        with (directory/f'client{index}.log').open('w+') as log:
                            with subprocess.Popen(args, cwd=directory, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True) as client:
                                try:
                                    deadline = time.monotonic()+6
                                    while not (directory/f'session{index}.pem').exists():
                                        if client.poll() is not None or time.monotonic() >= deadline: raise TimeoutError('session ticket acquisition')
                                        time.sleep(.02)
                                    client.stdin.close()
                                    client.wait(timeout=3)
                                finally: stop(client)
                        raw = (directory/f'client{index}.log').read_text()
                        lines = public_lines(raw)
                        assert any(line.startswith('New,' if index == 0 else 'Reused,') for line in lines)
                        if index == 2: assert 'Early data was accepted' in lines
                        assert client.returncode == 0
                        print(json.dumps({'connection_index': index, 'client_command': args, 'summary': lines,
                            'ticket_file_created': True, 'client_exit_after_stdin_eof': client.returncode}), flush=True)
                    server.wait(timeout=5)
                finally: stop(server)
            summary = public_lines((directory/'server.log').read_text())
            assert server.returncode == 0 and 'LAB25-EARLY-SAFE' in summary
            print(json.dumps({'server_summary': summary, 'server_exit': server.returncode,
                'early_text_observed': any('LAB25-EARLY-SAFE' in line for line in summary)}), flush=True)
    print(json.dumps({'temporary_secrets_cleaned': True, 'owned_processes_stopped': True}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args(); self_check()
    if not args.self_check: lab()


if __name__ == '__main__': main()
