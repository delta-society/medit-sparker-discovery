#!/usr/bin/env python3
"""Week 3 PDF-only one-time terminal connection bridge (stdlib, Python 3.9+).

Capabilities live only in a private local state file, never CLI output.
No participant cookies, source, transcript, or Camp credentials are read.
"""
import argparse
from contextlib import contextmanager
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any
import webbrowser

import evaluation
from plan import require, safe_path, ident
from portable import configure_stdio

PRODUCTION = 'https://leaderboard-production-eac2.up.railway.app'
MAX_PDF = 5 * 1024 * 1024


class RetryLater(Exception):
    pass


class AuthenticationRequired(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value, local_test=False):
    if value == PRODUCTION:
        return value
    p = urllib.parse.urlsplit(value)
    require(local_test and p.scheme == 'http' and p.hostname in ('127.0.0.1', 'localhost', '::1')
            and not p.username and not p.password and not p.path and not p.query and not p.fragment,
            '고정 production origin만 허용합니다. 로컬 HTTP는 --local-test가 필요합니다.')
    require(p.port is not None, '로컬 시험 포트가 필요합니다')
    return value


def current_pdf(root):
    """Load the full revision chain; never accept an arbitrary PDF path."""
    root = safe_path(root)
    r = evaluation.load(root)
    require(r['status'] == 'confirmed', '최신 평가서가 confirmed가 아닙니다. 다시 검토하세요.')
    folder = safe_path(root / ('pdf-r%06d' % r['revision']))
    receipt = evaluation.read(folder / 'receipt.json')
    require(receipt.get('digest') == r['digest'], 'PDF 평가 digest 불일치')
    # Old 0.11 PDFs have no byte receipt. Do not retroactively trust arbitrary bytes.
    require(receipt.get('sha256'), '구버전 PDF: evaluation.py pdf --refresh로 같은 confirmed 평가서를 다시 출력하세요.')
    pdf = safe_path(folder / 'evaluation.pdf')
    require(0 < pdf.stat().st_size <= MAX_PDF, 'PDF는 5MiB 이하만 허용합니다')
    data = pdf.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    require(data.startswith(b'%PDF-') and sha == receipt['sha256'], 'PDF SHA/magic 불일치')
    require(safe_path(folder / 'evaluation.html').read_text(encoding='utf-8') == evaluation.document(r),
            'PDF 원본이 현재 confirmed 평가서와 다릅니다')
    return r, data, dict(week=3, filename='evaluation.pdf', size=len(data), sha256=sha)


def private_write(path, state):
    fd, tmp = tempfile.mkstemp(prefix='.intent-', dir=path.parent)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def locked(path):
    # OS lock releases after process death; unlike mkdir locks it is resumable.
    path = safe_path(path)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
    os.chmod(path, 0o600)
    with os.fdopen(fd, 'r+b') as f:
        if os.name == 'nt':
            import msvcrt
            if not path.stat().st_size:
                f.write(b'0'); f.flush()
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise ValueError('이미 제출 helper가 실행 중입니다') from None
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise ValueError('이미 제출 helper가 실행 중입니다') from None
        yield


class Client:
    def __init__(self, base, timeout=15):
        self.base, self.timeout = base, timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, action, payload, token=None, content_type='application/json'):
        data = json.dumps(payload).encode() if isinstance(payload, dict) else payload
        headers = {'Content-Type': content_type, 'Accept': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(self.base + '/api/report-submissions/' + action, data=data, headers=headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read(65537)
            require(len(raw) <= 65536, '서버 응답 크기 초과')
            result = json.loads(raw)
            require(isinstance(result, dict), '서버 응답 형식 오류')
            return result
        except urllib.error.HTTPError as e:
            if e.code >= 500 or e.code == 429:
                raise RetryLater('서버가 일시적으로 응답하지 않습니다') from None
            if e.code in (401, 403):
                raise AuthenticationRequired('제출 연결을 다시 확인해야 합니다') from None
            # Never echo server bodies, headers, URL or token-bearing exceptions.
            raise ValueError('제출 API 거절 (HTTP %d)' % e.code) from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
            raise RetryLater('통신 결과 미확정') from None
        except (json.JSONDecodeError, UnicodeError):
            raise RetryLater('응답 해석 실패; 같은 intent를 재조회하세요') from None


def receipt_check(response, state, base):
    require(response.get('id') == state['id'], 'intent 응답 불일치')
    r = response.get('receipt')
    require(isinstance(r, dict), '서버 receipt가 없습니다')
    require(all(r.get(k) == state['metadata'][k] for k in ('week', 'filename', 'sha256', 'size')),
            '서버 receipt PDF SHA/metadata 불일치')
    require(isinstance(r.get('submission_id'), str) and r['submission_id']
            and isinstance(r.get('received_at'), str) and r['received_at']
            and r.get('url') == base + '/?view=learning', '서버 receipt 형식 오류')
    # Return only the public contract, never arbitrary response fields.
    return {k: r[k] for k in ('submission_id', 'week', 'filename', 'sha256', 'size', 'received_at', 'url')}


def upload(client, state, data):
    require(isinstance(state.get('metadata'), dict), '승인 파일 metadata 필요')
    name = state['metadata']['filename']
    require(name in ('week1-plan.zip', 'week2-implementation.zip', 'evaluation.pdf', 'final-code-and-report.zip'), '지원 파일 이름 오류')
    mime = 'application/pdf' if state['metadata']['week'] == 3 else 'application/zip'
    boundary = 'sparker' + uuid.uuid4().hex
    body = ('--' + boundary + '\r\nContent-Disposition: form-data; name="id"\r\n\r\n'
            + state['id'] + '\r\n--' + boundary
            + '\r\nContent-Disposition: form-data; name="file"; filename="' + name + '"'
            + '\r\nContent-Type: ' + mime + '\r\n\r\n').encode() + data + ('\r\n--' + boundary + '--\r\n').encode()
    return client.request('upload', body, state['upload_token'], 'multipart/form-data; boundary=' + boundary)


def config_directory(base):
    directory = safe_path(Path.home() / '.config' / 'sparker-report' / hashlib.sha256(base.encode()).hexdigest())
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    return directory


def logout(base, scope=3):
    require(scope in (1, 2, 3, 4), '제출 scope 오류')
    path = config_directory(base) / ('device.json' if scope == 3 else 'device-week%d.json' % scope)
    if path.exists():
        Client(base).request('revoke', {}, evaluation.read(path)['token'])
        path.unlink()
    return {'status': 'disconnected'}


def submit(root, *, consent=False, base=PRODUCTION, local_test=False, no_browser=False,
           wait=120, interval=2, timeout=15, artifact_loader=None, scope=3):
    require(consent, '보고서 검토 확인과 외부 제출 동의는 다릅니다. 제출 요청이 필요합니다.')
    base = origin(base, local_test)
    require(wait >= 0 and interval > 0 and timeout > 0, '대기 설정 오류')
    root = safe_path(root)
    loader = artifact_loader or current_pdf
    require(scope in (1, 2, 3, 4), '제출 scope 오류')
    r, data, metadata = loader(root)
    require(metadata['week'] == scope, '파일/권한 scope 불일치')
    directory = config_directory(base)
    credential_path = directory / ('device.json' if scope == 3 else 'device-week%d.json' % scope)
    credential = evaluation.read(credential_path) if credential_path.exists() else {}
    key = hashlib.sha256((str(root) + ':' + str(r['revision']) + ':' + metadata['sha256']).encode()).hexdigest()
    state_path = safe_path(directory / (key + '.json'))
    with locked(directory / (key + '.lock')):
        client = Client(base, timeout)
        if state_path.exists():
            previous = evaluation.read(state_path)
            if previous.get('phase') == 'expired' or (previous.get('phase') == 'preparing' and time.time() - previous.get('started', 0) > 600):
                state_path.unlink()
        if state_path.exists():
            os.chmod(state_path, 0o600)
            state = evaluation.read(state_path)
            require(state.get('base') == base and state.get('metadata') == metadata, '저장된 intent 불일치')
            require(state.get('phase') != 'preparing',
                    'prepare 응답 미확정: 자동 재생성하지 않습니다. 서버 10분 만료 후 intent 파일을 별도 보관하고 다시 요청하세요.')
        else:
            state: dict[str, Any] = dict(base=base, metadata=metadata, phase='preparing', started=time.time())
            private_write(state_path, state)  # ambiguous prepare must not create another intent
            try:
                try:
                    prepared = client.request('prepare', metadata, credential.get('token'))
                except AuthenticationRequired:
                    # Rejection precedes intent creation; reconnect without deleting a
                    # possibly accepted upload or guessing its outcome.
                    if not credential.get('token'):
                        raise
                    credential_path.unlink(missing_ok=True)
                    credential = {}
                    prepared = client.request('prepare', metadata)
            except RetryLater:
                return dict(status='prepare_unknown', resumable=False)
            require(isinstance(prepared.get('id'), str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', prepared['id']), 'intent id 오류')
            require(isinstance(prepared.get('upload_token'), str) and re.fullmatch(r'[A-Za-z0-9_-]{32,256}', prepared['upload_token']), 'upload capability 오류')
            approval = prepared.get('approval_url', '')
            prefix = base + '/?view=learning#submit-report=' + prepared['id'] + ':'
            require(approval.startswith(prefix) and re.fullmatch(r'[A-Za-z0-9_-]{32,256}', approval[len(prefix):]), 'approval URL 오류')
            state.update({k: prepared[k] for k in ('id', 'upload_token', 'approval_url', 'expires_at')})
            state['phase'] = 'pending_authorization'
            private_write(state_path, state)
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', state['id']), '저장 intent 오류')
        deadline = time.monotonic() + wait
        opened = False
        while True:
            try:
                status = client.request('status', {'id': state['id']}, state['upload_token'])
                require(status.get('id') == state['id'], 'intent 응답 불일치')
                phase = status.get('status')
                require(phase in ('pending_authorization', 'authorized', 'submitted', 'expired'), '서버 상태 오류')
                if phase == 'submitted':
                    receipt = receipt_check(status, state, base)
                    state.update(phase='submitted', receipt=receipt)
                    private_write(state_path, state)
                    return dict(status='submitted', receipt=receipt)
                if phase == 'expired':
                    state['phase'] = phase
                    private_write(state_path, state)
                    return dict(status='expired', resumable=False)
                if phase == 'pending_authorization' and not opened and not no_browser:
                    prefix = base + '/?view=learning#submit-report=' + state['id'] + ':'
                    require(state['approval_url'].startswith(prefix)
                            and re.fullmatch(r'[A-Za-z0-9_-]{32,256}', state['approval_url'][len(prefix):]), '저장 approval URL 오류')
                    require(webbrowser.open(state['approval_url'], new=2), '브라우저 자동 열기 실패. 기본 브라우저 설정 후 같은 명령을 재실행하세요.')
                    opened = True
                if phase == 'authorized':
                    if not credential.get('token'):
                        if not state.get('device_candidate'):
                            state['device_candidate'] = secrets.token_urlsafe(32)
                            private_write(state_path, state)
                        grant = client.request('exchange', {'id': state['id'], 'device_token': state['device_candidate']}, state['upload_token'])
                        credential = {'token': state['device_candidate'], 'expires_at': grant['expires_at']}
                        private_write(credential_path, credential)
                    latest, current, current_meta = loader(root)
                    require(latest == r and current_meta == metadata and current == data, '대기 중 평가/PDF 변경: 재검토 필요')
                    upload(client, state, data)
                    # Upload acknowledgement alone is never success; independent status readback.
                    status = client.request('status', {'id': state['id']}, state['upload_token'])
                    if status.get('status') == 'submitted':
                        receipt = receipt_check(status, state, base)
                        state.update(phase='submitted', receipt=receipt)
                        private_write(state_path, state)
                        return dict(status='submitted', receipt=receipt)
            except RetryLater:
                pass  # next iteration always queries the same intent before any upload
            if time.monotonic() >= deadline:
                return dict(status='pending', resumable=True, message='접수 미확정. 같은 명령으로 재개하세요.')
            time.sleep(min(interval, max(0, deadline - time.monotonic())))


def main():
    configure_stdio()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default='.sparker-evaluation')
    p.add_argument('--case', default='my-product')
    p.add_argument('--scope', type=int, choices=(1, 2, 3, 4), default=3, help='해제할 제출 주차')
    p.add_argument('--logout', action='store_true', help='제출 전용 터미널 연결 해제')
    p.add_argument('--submit', action='store_true', help='사용자가 외부 제출을 요청한 경우에만 지정')
    p.add_argument('--origin', default=PRODUCTION)
    p.add_argument('--local-test', action='store_true')
    p.add_argument('--no-browser', action='store_true', help='deterministic 시험용')
    p.add_argument('--wait', type=float, default=120)
    p.add_argument('--interval', type=float, default=2)
    p.add_argument('--timeout', type=float, default=15)
    a = p.parse_args()
    try:
        if a.logout:
            print(json.dumps(logout(origin(a.origin, a.local_test), a.scope)))
            return 0
        ident(a.case)
        result = submit(safe_path(Path(a.root).absolute() / a.case), consent=a.submit,
                        base=a.origin, local_test=a.local_test, no_browser=a.no_browser,
                        wait=a.wait, interval=a.interval, timeout=a.timeout)
        if result['status'] == 'expired':
            # The server proved this intent cannot write. Release its lock and
            # renew once; ambiguous/failed requests never take this path.
            result = submit(safe_path(Path(a.root).absolute() / a.case), consent=a.submit,
                            base=a.origin, local_test=a.local_test, no_browser=a.no_browser,
                            wait=a.wait, interval=a.interval, timeout=a.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'submitted' else 2
    except (ValueError, OSError, KeyError, TypeError):
        # Detailed data/paths in exceptions may contain participant input; no traceback.
        print(json.dumps({'status': 'blocked', 'message': '제출 중단: 최신 confirmed PDF/receipt, origin, 브라우저 및 private intent 상태를 확인하세요.'}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
