#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
# How to run: python3 lab.py; python3 lab.py --self-check
"""Bounded loopback TLS 1.3 identity experiment; disposable private keys only."""
import argparse
import hashlib
import json
import os
import platform
import secrets
import socket
import ssl
import subprocess
import tempfile
import threading
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


def client_context(cafile: Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=str(cafile))
    context.hostname_checks_common_name = False
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    assert context.verify_flags & ssl.VERIFY_X509_STRICT
    assert context.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert context.keylog_filename is None
    return context


def receive(stream: ssl.SSLSocket) -> bytes:
    result = bytearray()
    while len(result) < 32:
        part = stream.recv(32-len(result))
        if not part: raise EOFError('challenge truncated')
        result.extend(part)
    return bytes(result)


def scenario(directory: Path, trusted: bool, hostname: str) -> None:
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.minimum_version = server_context.maximum_version = ssl.TLSVersion.TLSv1_3
    server_context.load_cert_chain(directory/'leaf.pem', directory/'leaf.key')
    client = client_context(directory/('root.pem' if trusted else 'other.pem'))
    server_events = []
    with socket.socket() as listener:
        listener.settimeout(5); listener.bind(('127.0.0.1', 0)); listener.listen(1)
        address = listener.getsockname()
        def serve() -> None:
            phase = 'accept'
            try:
                raw, peer = listener.accept()
                with raw:
                    raw.settimeout(5)
                    phase = 'handshake'
                    with server_context.wrap_socket(raw, server_side=True) as tls:
                        phase = 'application'
                        data = receive(tls)
                        tls.sendall(data)
                        server_events.append({'handshake': 'success', 'peer': peer, 'version': tls.version(),
                            'cipher': tls.cipher(), 'received_hex': data.hex(), 'echoed_hex': data.hex()})
            except (ssl.SSLError, OSError, EOFError) as error:
                server_events.append({'handshake_or_io_error': type(error).__name__, 'message': str(error), 'phase': phase, 'application_exchange_started': phase == 'application'})
        thread = threading.Thread(target=serve)
        thread.start()
        outcome = {}
        challenge = secrets.token_bytes(32)
        try:
            with socket.create_connection(address, timeout=5) as raw:
                with client.wrap_socket(raw, server_hostname=hostname) as tls:
                    tls.sendall(challenge); echoed = receive(tls)
                    assert echoed == challenge
                    certificate = tls.getpeercert()
                    outcome = {'handshake': 'success', 'version': tls.version(), 'cipher': tls.cipher(),
                        'peer_certificate': certificate, 'peer_der_sha256': hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest(),
                        'challenge_hex': challenge.hex(), 'echo_hex': echoed.hex()}
        except ssl.SSLCertVerificationError as error:
            outcome = {'handshake': 'verification-failed', 'verify_code': error.verify_code,
                       'verify_message': error.verify_message, 'application_bytes': 0}
        finally:
            thread.join(timeout=7)
        assert not thread.is_alive()
        success = trusted and hostname == 'server.lab.test'
        assert (outcome['handshake'] == 'success') == success
        assert len(server_events) == 1
        if success: assert server_events[0]['received_hex'] == challenge.hex()
        else: assert server_events[0]['phase'] == 'handshake' and not server_events[0]['application_exchange_started']
        print(json.dumps({'trusted_root': trusted, 'server_hostname': hostname, 'connection_address': address,
            'verify_flags': int(client.verify_flags), 'check_hostname': client.check_hostname,
            'common_name_fallback': client.hostname_checks_common_name, 'trust_store_stats': client.cert_store_stats(),
            'client': outcome, 'server': server_events, 'owned_thread_stopped': True}), flush=True)


def self_check() -> None:
    assert ssl.HAS_TLSv1_3
    assert hashlib.sha256(b'abc').hexdigest() == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    print(json.dumps({'offline_self_check': 'TLS13 API availability and digest known vector only'}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    self_check()
    if args.self_check: return
    keylog_present = os.environ.pop('SSLKEYLOGFILE', None) is not None
    print(json.dumps({'environment': platform.platform(), 'python': platform.python_version(),
        'python_ssl': ssl.OPENSSL_VERSION, 'SSLKEYLOGFILE_removed_if_present': keylog_present}), flush=True)
    with tempfile.TemporaryDirectory(prefix='network24-') as temporary:
        directory = Path(temporary)
        command(directory, ['version']); certificates(directory)
        scenario(directory, True, 'server.lab.test')
        scenario(directory, True, 'wrong.lab.test')
        scenario(directory, False, 'server.lab.test')
    print(json.dumps({'temporary_keys_cleaned': True, 'owned_listeners_closed': True}), flush=True)


if __name__ == '__main__': main()
