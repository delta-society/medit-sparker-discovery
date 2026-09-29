"""Synthetic HTTP contract tests, NOT live login/model/browser acceptance tests."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.parser import BytesParser
from email.policy import default
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import evaluation as e
import submission_bridge as b

PDF = b'%PDF-1.4\n% SYNTHETIC fixture, not a participant report\n%%EOF\n'


def fixture(root):
    d = e.template()
    d['title'] = 'SYNTHETIC bridge fixture (not participant)'
    for row in d['criteria']:
        row['reviewed'] = True
    r = e.save(root, d)
    r = e.save(root, d, '합성 시험 확인 — 실제 사람 검토 아님', r['digest'])
    with patch.object(e, 'print_pdf', return_value=(PDF, {'synthetic': True})):
        e.export(root, r)
    return r


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'private, no-store')
        self.end_headers()
        try:
            self.wfile.write(json.dumps(data).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass  # synthetic timeout intentionally closed the socket

    def do_POST(self):
        s = self.server
        action = self.path.rsplit('/', 1)[-1]
        s.calls.append(action)
        raw = self.rfile.read(int(self.headers['Content-Length']))
        if action == 'prepare':
            s.prepares += 1
            s.metadata = json.loads(raw)
            assert set(s.metadata) == {'week', 'filename', 'size', 'sha256'}
            assert s.metadata['week'] == 3 and 'Authorization' not in self.headers
            assert 'Cookie' not in self.headers
            self.respond(dict(id='synthetic-intent', upload_token='u'*43,
                              approval_url=s.base+'/?view=learning#submit-report=synthetic-intent:'+'a'*43,
                              expires_at='2099-01-01T00:00:00Z'))
            return
        if action in ('preview', 'authorize'):
            payload = json.loads(raw)
            if self.headers.get('Cookie') != 'session=synthetic' or self.headers.get('Origin') != s.base or payload != {'id': 'synthetic-intent', 'approval_token': 'a'*43}:
                self.respond({}, 403); return
            if action == 'authorize':
                s.phase = 'authorized'
            self.respond(dict(id='synthetic-intent', status=s.phase, **s.metadata))
            return
        assert 'Cookie' not in self.headers
        if self.headers.get('Authorization') != 'Bearer '+'u'*43:
            self.respond({}, 403); return
        if action == 'exchange':
            self.respond({'expires_at':'2099-01-01T00:00:00Z'}); return
        if action == 'upload':
            msg = BytesParser(policy=default).parsebytes(('Content-Type: '+self.headers['Content-Type']+'\r\n\r\n').encode()+raw)
            parts = {p.get_param('name', header='content-disposition'): p for p in msg.iter_parts()}
            assert set(parts) == {'id', 'file'}
            assert parts['id'].get_payload(decode=True) == b'synthetic-intent'
            data = parts['file'].get_payload(decode=True)
            if s.phase not in ('authorized', 'submitted') or hashlib.sha256(data).hexdigest() != s.metadata['sha256']:
                self.respond({}, 409); return
            if s.phase != 'submitted':
                s.uploads += 1
                s.bytes = data
                s.phase = 'submitted'
            if s.delay_upload_response:
                import time
                time.sleep(.5)
            if s.lose_upload_response:
                s.lose_upload_response = False
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
        elif action == 'status':
            assert json.loads(raw) == {'id': 'synthetic-intent'}
            s.statuses += 1
            if s.fail_readback and s.phase == 'submitted':
                self.respond({}, 503); return
        result = dict(id='synthetic-intent', status=s.phase)
        if s.phase == 'submitted':
            result['receipt'] = dict(submission_id='synthetic-submission', received_at='2026-01-01T00:00:00Z', url=s.base+'/?view=learning', **s.metadata)
            if s.bad_receipt:
                result['receipt']['sha256'] = '0'*64
        self.respond(result)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home_patch = patch.dict('os.environ', {'HOME':str(Path(self.tmp.name).resolve())})
        self.home_patch.start()
        self.root = Path(self.tmp.name).resolve() / 'synthetic'
        self.r = fixture(self.root)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        s = self.server
        s.base = 'http://127.0.0.1:%s' % s.server_port
        s.phase = 'pending_authorization'
        s.prepares = s.uploads = s.statuses = 0
        s.calls = []
        s.bad_receipt = s.fail_readback = s.lose_upload_response = s.delay_upload_response = False
        self.thread = threading.Thread(target=s.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.home_patch.stop()
        self.tmp.cleanup()

    def run_bridge(self, **kwargs):
        return b.submit(self.root, consent=True, base=self.server.base, local_test=True,
                        wait=kwargs.pop('wait', 0), interval=.01, timeout=.3, **kwargs)

    def approve(self, url, **kwargs):
        # Real HTTP through synthetic browser session, not a production OAuth assertion.
        import urllib.request
        p = {'id': 'synthetic-intent', 'approval_token': 'a'*43}
        for action in ('preview', 'authorize'):
            req = urllib.request.Request(self.server.base+'/api/report-submissions/'+action,
                  data=json.dumps(p).encode(), headers={'Cookie': 'session=synthetic', 'Origin': self.server.base, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, 200)
        return True

    def test_browser_success_readback_and_resume_no_duplicate(self):
        with patch.object(b.webbrowser, 'open', side_effect=self.approve) as browser:
            result = self.run_bridge(wait=.3)
            self.assertEqual(browser.call_count, 1)
        self.assertEqual(result['status'], 'submitted')
        self.assertEqual(self.server.bytes, PDF)
        self.assertGreaterEqual(self.server.statuses, 3)
        self.assertEqual(self.server.calls[-1], 'status')
        self.assertEqual(self.run_bridge(no_browser=True), result)
        self.assertEqual(self.server.prepares, 1)
        self.assertEqual(self.server.uploads, 1)
        private = next(b.config_directory(self.server.base).glob('*.json'))
        if sys.platform != 'win32':
            self.assertEqual(private.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('upload_token', json.dumps(result))
        self.assertNotIn('approval_url', json.dumps(result))

    def test_timeout_resume_same_intent(self):
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'pending')
        self.approve('synthetic')
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'submitted')
        self.assertEqual(self.server.prepares, 1)

    def test_lost_upload_response_resumes_status_without_duplicate(self):
        self.server.phase = 'authorized'
        self.server.lose_upload_response = True
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'pending')
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'submitted')
        self.assertEqual(self.server.uploads, 1)
        self.assertEqual(self.server.calls.count('upload'), 1)

    def test_actual_http_timeout_then_resume_no_duplicate(self):
        self.server.phase = 'authorized'
        self.server.delay_upload_response = True
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'pending')
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'submitted')
        self.assertEqual(self.server.prepares, 1)
        self.assertEqual(self.server.calls.count('upload'), 1)

    def test_upload_ack_is_not_success_without_readback(self):
        self.server.phase = 'authorized'; self.server.fail_readback = True
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'pending')
        self.server.fail_readback = False
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'submitted')
        self.assertEqual(self.server.calls.count('upload'), 1)

    def test_stale_draft_rejected_before_prepare(self):
        e.save(self.root, self.r['document'])
        with self.assertRaises(ValueError): self.run_bridge(no_browser=True)
        self.assertEqual(self.server.prepares, 0)

    def test_new_confirmed_requires_new_pdf(self):
        r = e.save(self.root, self.r['document'])
        e.save(self.root, r['document'], '합성 재확인', r['digest'])
        with self.assertRaises(OSError): self.run_bridge(no_browser=True)
        self.assertEqual(self.server.prepares, 0)

    def test_pdf_sha_mismatch_rejected(self):
        (self.root/'pdf-r000002/evaluation.pdf').write_bytes(PDF+b'changed')
        with self.assertRaises(ValueError): self.run_bridge(no_browser=True)
        self.assertEqual(self.server.prepares, 0)

    def test_receipt_sha_mismatch_rejected(self):
        self.server.phase = 'authorized'; self.server.bad_receipt = True
        with self.assertRaises(ValueError): self.run_bridge(no_browser=True)

    def test_real_cli_json_has_receipt_no_capabilities(self):
        import subprocess
        self.server.phase = 'authorized'
        cmd = [sys.executable, str(Path(b.__file__)), '--root', str(self.root.parent),
               '--case', self.root.name, '--submit', '--no-browser', '--local-test',
               '--origin', self.server.base, '--wait', '0']
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'submitted')
        self.assertNotIn('u'*43, result.stdout + result.stderr)
        self.assertNotIn('a'*43, result.stdout + result.stderr)
        self.assertNotIn('approval_url', result.stdout)

    def test_consent_and_origin_boundary(self):
        with patch.object(b.webbrowser, 'open') as browser:
            with self.assertRaises(ValueError): b.submit(self.root)
            for value in ('https://evil.invalid', self.server.base, b.PRODUCTION+'/x'):
                with self.assertRaises(ValueError): b.submit(self.root, consent=True, base=value)
            browser.assert_not_called()
        for value in ('http://localhost:80/path','http://user@localhost:80','http://localhost.evil:80'):
            with self.assertRaises(ValueError): b.origin(value, True)
        self.assertEqual(self.server.prepares, 0)

    def test_edit_while_waiting_stops_upload(self):
        def changed(url, **kwargs):
            self.approve(url)
            e.save(self.root, self.r['document'])
            return True
        with patch.object(b.webbrowser, 'open', side_effect=changed):
            with self.assertRaises(ValueError): self.run_bridge(wait=.3)
        self.assertEqual(self.server.uploads, 0)

    def test_legacy_pdf_requires_rerender_not_retroactive_hash(self):
        path = self.root/'pdf-r000002/receipt.json'
        receipt = json.loads(path.read_text()); del receipt['sha256']; path.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError): self.run_bridge(no_browser=True)
        with patch.object(e, 'print_pdf', return_value=(PDF, {'synthetic': True})) as render:
            e.export(self.root, e.load(self.root), refresh=True)
            self.assertEqual(render.call_count, 1)
        b.current_pdf(self.root)

    def test_expired_reexecution_recovers_new_intent(self):
        self.server.phase = 'expired'
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'expired')
        self.assertEqual(self.run_bridge(no_browser=True)['status'], 'expired')
        self.assertEqual(self.server.prepares, 2)

    def test_ambiguous_prepare_never_automatically_reprepared(self):
        with patch.object(b.Client, 'request', side_effect=b.RetryLater()):
            self.assertEqual(self.run_bridge(no_browser=True)['status'], 'prepare_unknown')
        with self.assertRaises(ValueError): self.run_bridge(no_browser=True)
        self.assertEqual(self.server.prepares, 0)

    def test_wrong_upload_token_and_unapproved_denied(self):
        self.run_bridge(no_browser=True)
        client = b.Client(self.server.base)
        with self.assertRaises(ValueError): client.request('status', {'id':'synthetic-intent'}, 'wrong')
        state = dict(id='synthetic-intent', upload_token='u'*43)
        with self.assertRaises(ValueError): b.upload(client, state, PDF)
        self.server.phase = 'authorized'
        with self.assertRaises(ValueError): b.upload(client, state, PDF+b'wrong-sha')
        self.assertEqual(self.server.uploads, 0)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--fixture':
        root = Path(sys.argv[2]).absolute()
        fixture(root)
        print('SYNTHETIC ONLY fixture created:', root)
    else:
        unittest.main()
