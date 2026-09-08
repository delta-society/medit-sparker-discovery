#!/usr/bin/env python3
"""Synthetic HTTP integration against an isolated participant-app checkout.

Requires that checkout's npm dependencies, Node 22+, and Python 3.9+.
No deployment, real account or real transcript. All requests stay on loopback.
"""
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugin/scripts'))
import camp_submit as camp
from plan import Store, template

EXPECTED_SHA = '439d2ba491cef5f2a4c01947a03a1577491672d9'


def verify(app_root):
    app = Path(app_root).resolve()
    actual_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=app, text=True).strip()
    if actual_sha != EXPECTED_SHA:
        raise RuntimeError('Re-read the participant API before testing another source revision')
    with tempfile.TemporaryDirectory(prefix='sparker-camp-TEST-ONLY-') as temp:
        base = Path(temp).resolve()
        project = base / 'synthetic-project'
        project.mkdir()
        store = Store(project / '.sparker-discovery')
        store.write('synthetic-case', 'new', plan=template(linked=True))
        sessions = []
        for index in range(2):
            sid = str(uuid.uuid4())
            path = base / (sid + '.jsonl')
            row = {'type': 'user', 'sessionId': sid, 'cwd': str(project),
                   'message': {'role': 'user', 'content': f'TEST ONLY 합성 학습 기록 {index}'}}
            path.write_bytes((json.dumps(row, ensure_ascii=False) + '\n').encode('utf-8'))
            sessions.append(path)
        bundle = project / '.sparker-submissions' / 'week1-synthetic.zip'
        prepared = camp.prepare(store.root, 'synthetic-case', 1, 1, project, sessions, bundle, True)
        bytes_ = bundle.read_bytes()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        origin = f'http://127.0.0.1:{port}'
        key = secrets.token_urlsafe(32)
        password = 'TEST-only-' + secrets.token_hex(24) + 'Aa!'
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('SPARKER_', 'GITHUB_', 'NEXT_PUBLIC_')) and k != 'NODE_OPTIONS'}
        env.update(SPARKER_MODE='live', SPARKER_DEMO='0', SPARKER_ALLOW_LOOPBACK_HTTP='1',
                   SPARKER_ORIGIN=origin, SPARKER_DB=str(base / 'test.sqlite'),
                   SPARKER_ADMIN_USERNAME='test-admin', SPARKER_ADMIN_LABEL='TEST ONLY Admin',
                   SPARKER_ADMIN_PASSWORD=password, SPARKER_CONSOLE_KEY=key,
                   SPARKER_MANAGEMENT_MODE='legacy', NEXT_TELEMETRY_DISABLED='1')
        def client():
            return urllib.request.build_opener(urllib.request.ProxyHandler({}),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        anonymous, a, b = client(), client(), client()

        def request(client_, route, data=None, body=None, content_type=None, management=False, extra=None):
            headers = {}
            if data is not None:
                body = json.dumps(data).encode()
                content_type = 'application/json'
            if body is not None:
                headers.update({'Origin': origin, 'Content-Type': content_type})
            if management:
                headers.update({'Authorization': 'Bearer ' + key, 'X-Console-Actor': 'test-admin',
                                'X-Request-ID': str(uuid.uuid4())})
            headers.update(extra or {})
            req = urllib.request.Request(origin + '/api/' + route, data=body, headers=headers)
            try:
                response = client_.open(req, timeout=45)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, response.read(), response.headers

        def upload(client_, data=bytes_, **kwargs):
            boundary = '----sparker-' + secrets.token_hex(12)
            parts = []
            fields = {'week': '1', **kwargs.pop('fields', {})}
            for name, value in fields.items():
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="week1-synthetic.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode() + data + b'\r\n')
            parts.append(f'--{boundary}--\r\n'.encode())
            return request(client_, 'submissions', body=b''.join(parts),
                           content_type='multipart/form-data; boundary=' + boundary, **kwargs)

        results = []
        def check(condition, label):
            if not condition:
                raise AssertionError(label)
            results.append(label)

        with (base / 'server.log').open('wb') as log:
            child = subprocess.Popen(['node', 'node_modules/next/dist/bin/next', 'dev',
                                      '--hostname', '127.0.0.1', '--port', str(port)],
                                     cwd=app, env=env, stdout=log, stderr=log,
                                     start_new_session=True)
            try:
                deadline = time.monotonic() + 90
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError('Isolated server exited before readiness')
                    try:
                        if request(anonymous, 'health')[0] == 200:
                            break
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError('Isolated server did not become ready')
                check(upload(anonymous)[0] == 401, 'unauthenticated upload rejected')
                for client_, suffix, pid in [(a, 'a', 'P01'), (b, 'b', 'P02')]:
                    status, body, _ = request(anonymous, 'admin/participants', management=True,
                        data={'id': 'TEST-' + suffix, 'label': 'TEST ONLY ' + suffix,
                              'username': 'test-' + suffix, 'participantId': pid, 'mappingVerified': True})
                    check(status == 201, 'synthetic participant ' + suffix + ' provisioned locally')
                    code = json.loads(body)['code']
                    check(request(client_, 'activate', data={'username': 'test-' + suffix,
                          'code': code, 'password': password})[0] == 200, 'synthetic participant ' + suffix + ' authenticated')
                check(upload(a, extra={'Origin': 'https://wrong-origin.invalid'})[0] == 403,
                      'cross-origin upload rejected')
                check(upload(a, fields={'user_id': 'TEST-b'})[0] == 400, 'forged participant identity rejected')
                status, body, _ = upload(a)
                check(status == 201, 'generated Camp ZIP accepted by actual submission route')
                first_id = json.loads(body)['id']
                status, downloaded, headers = request(a, 'files/' + first_id)
                check(status == 200 and downloaded == bytes_, 'participant download equals prepared bytes')
                check('attachment' in headers['Content-Disposition'], 'download treated as attachment')
                downloaded_path = base / 'downloaded.zip'
                downloaded_path.write_bytes(downloaded)
                check(camp.inspect(downloaded_path)['sha256'] == prepared['sha256'], 'download passes Camp manifest and hash validation')
                check(request(anonymous, 'files/' + first_id)[0] == 401, 'unauthenticated download rejected')
                check(request(b, 'files/' + first_id)[0] == 404, 'another participant cannot read the file')
                status, downloaded, _ = request(anonymous, 'admin/files/' + first_id, management=True)
                check(status == 200 and downloaded == bytes_, 'authenticated operator download equals prepared bytes')
                status, body, _ = upload(a)
                second_id = json.loads(body)['id']
                check(status == 201 and second_id != first_id, 're-upload creates an explicit new server history entry')
                check(request(a, 'files/' + first_id)[1] == bytes_, 'previous submission remains downloadable')
                status, body, _ = request(a, 'dashboard')
                dashboard = json.loads(body)
                check(status == 200 and len(dashboard['submissions']) == 2 and
                      sum(s['active'] for s in dashboard['submissions']) == 1,
                      'dashboard keeps history with one active submission')
                check(all(row['tokens'] == 0 for row in dashboard['entries']), 'assignment upload does not fabricate usage tokens')
                check(upload(a, data=b'x' * (camp.MAX_ZIP + 1))[0] in (400, 413), 'participant app rejects files over 5 MiB')
                return {'result': 'PASS', 'participant_app_sha': actual_sha,
                        'mode': 'isolated Next HTTP server, synthetic users/data only',
                        'checks': results, 'bundle_bytes': len(bytes_), 'bundle_sha256': prepared['sha256']}
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', required=True, help='isolated participant-app checkout with npm ci completed')
    args = parser.parse_args()
    print(json.dumps(verify(args.app_root), ensure_ascii=False, indent=2))
