#!/usr/bin/env python3
"""Local Week 2 records; no code generation, execution, network, or upload."""
import argparse
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

from plan import PlanError, canonical, digest, ident, no_duplicates, require, safe_path
from camp_submit import stable_read, sha, SECRET_PATTERNS
from portable import configure_stdio

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024
MAX_FILES = 100
STAGES = ('scope', 'environment', 'implement', 'change', 'test', 'submit', 'paused',
          'bootstrap', 'spec', 'workstream', 'baseline', 'demo')
REQUIRED_KINDS = ('environment', 'execution', 'change', 'normal', 'exception', 'second_input')
KINDS = REQUIRED_KINDS + ('browser', 'replay', 'baseline', 'demo')
LESSON_PHASES = ('bootstrap', 'spec', 'workstream', 'baseline', 'improve', 'verify', 'demo')
LESSON_KEYS = ('phase', 'waiting_for', 'product_path', 'local_url', 'workstream',
               'acceptance_criteria', 'learner_observation')
ARCHIVES = {'.zip', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.7z', '.rar', '.jar', '.docx', '.xlsx', '.pptx'}
EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.sql', '.sh', '.ps1', '.r', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.cs', '.md', '.txt', '.json', '.toml', '.yaml', '.yml', '.csv'}


def text(value):
    require(isinstance(value, str) and 0 < len(value.strip()) <= 8000, '비어 있지 않은 짧은 문자열 필요')


def keys(value, names):
    require(isinstance(value, dict) and set(value) == set(names), '필드 불일치: ' + ', '.join(names))


def parse(data):
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(PlanError('비유한 수 금지')))


def relative(name):
    text(name)
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/'))
            and not re.search(r'[\\:\x00-\x1f]', name), '안전하지 않은 상대 경로')
    require(all(not x.endswith((' ', '.')) for x in p.parts), '모호한 경로 금지')
    return p


def intake(path, member=None):
    """Inspect entire bounded ZIP before reading one explicit MD/PDF; never extract."""
    path = safe_path(path)
    data = stable_read(path, MAX_TOTAL)
    name = path.name
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            require(0 < len(infos) <= MAX_FILES, 'ZIP 항목 수 한도')
            names, total = set(), 0
            for item in infos:
                # ZipInfo normalizes backslashes on Windows and truncates NULs.
                # Validate the original archive spelling, not only its projection.
                require(item.orig_filename == item.filename, '정규화된 ZIP 경로 금지')
                n = item.filename.rstrip('/') if item.is_dir() else item.filename
                relative(n)
                require(n.casefold() not in names, 'ZIP 중복 경로')
                names.add(n.casefold())
                mode = item.external_attr >> 16
                require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'ZIP 링크/특수 파일 금지')
                require(not item.flag_bits & 1, '암호화 ZIP 금지')
                require(PurePosixPath(n).suffix.lower() not in ARCHIVES, '중첩 archive 금지')
                total += item.file_size
                require(item.file_size <= MAX_FILE and total <= MAX_TOTAL
                        and item.file_size <= max(1, item.compress_size) * 100, 'ZIP 크기/압축률 한도')
                if not item.is_dir():
                    with z.open(item) as handle:
                        payload = handle.read(MAX_FILE + 1)
                    require(len(payload) == item.file_size, 'ZIP 크기 불일치')
                    require(not payload.startswith((b'PK\x03\x04', b'\x1f\x8b', b'7z\xbc\xaf', b'Rar!'))
                            and payload[257:262] != b'ustar', '위장 중첩 archive 금지')
            candidates = [i.filename for i in infos if not i.is_dir() and PurePosixPath(i.filename).suffix.lower() in ('.md', '.pdf')]
            if member is None:
                return {'status': 'choose_member', 'members': candidates, 'sha256': sha(data)}
            require(member in candidates, '명시한 MD/PDF 항목 없음')
            source_hash = sha(data)
            data = z.read(member)
            name = member
    else:
        require(member is None, 'member는 ZIP 전용')
        source_hash = sha(data)
    suffix = PurePosixPath(name).suffix.lower()
    require(suffix in ('.md', '.pdf') and len(data) <= MAX_FILE, '2 MiB 이하 MD/PDF 필요')
    result = {'name': name, 'source_sha256': source_hash, 'sha256': sha(data), 'member': member}
    if suffix == '.pdf':
        require(data.startswith(b'%PDF-'), 'PDF 헤더 불일치')
        result.update(status='needs_host_read', message='호스트 PDF 읽기로 실제 내용을 확인하세요. 스캔본/OCR 미지원이면 읽지 못했다고 알리고 MD 또는 텍스트를 요청하세요.')
    else:
        result.update(status='read', text=data.decode('utf-8-sig'))
    return result


def allowed(name, data):
    p = relative(name)
    banned = ('.env', '.git', 'node_modules', 'secret', 'credential', 'transcript', 'raw-session', 'raw_session', '.sparker', '.claude', '.ssh')
    require(not any(any(x in part.lower() for x in banned) for part in p.parts), '제출 금지 경로: ' + name)
    require(p.suffix.lower() in EXTENSIONS, '제출 파일 확장자 비허용: ' + name)
    require(len(data) <= MAX_FILE and b'\x00' not in data, '텍스트/크기 한도')
    data.decode('utf-8-sig')
    patterns = list(SECRET_PATTERNS.values()) + [rb'(?i)(?:api[_-]?key|password|secret|access[_-]?token)\s*[=:]\s*["\']?[^\s"\']{8,}', rb'"(?:sessionId|session_id)"\s*:.*"(?:messages|cwd|type)"']
    require(not any(re.search(pat, data) for pat in patterns), '비밀/원본 세션 의심 내용: ' + name)


def project_file(project, name):
    relative(name)
    return safe_path(project / name)


def validate_lesson(lesson):
    keys(lesson, LESSON_KEYS)
    for key in LESSON_KEYS:
        if key != 'acceptance_criteria':
            require(isinstance(lesson[key], str) and len(lesson[key]) <= 8000, '문자열 필요: lesson.' + key)
    require(lesson['phase'] in LESSON_PHASES, '알 수 없는 lesson 단계')
    require(lesson['waiting_for'] in ('none', 'learner', 'instructor'), 'lesson 대기 대상 오류')
    criteria = lesson['acceptance_criteria']
    require(isinstance(criteria, list) and len(criteria) <= 100, 'acceptance_criteria 목록 필요')
    for criterion in criteria:
        require(isinstance(criterion, str) and len(criterion) <= 8000, 'acceptance_criteria 문자열 필요')


def validate_state(s):
    fields = ('summary', 'feature', 'scope_confirmation', 'environment', 'structure', 'desired_change', 'change_confirmation', 'stage', 'next_action', 'blockers', 'evidence')
    # Do not inject defaults: existing version-1 records and their hashes stay unchanged.
    has_lesson = isinstance(s, dict) and 'lesson' in s
    keys(s, fields + (('lesson',) if has_lesson else ()))
    if has_lesson:
        validate_lesson(s['lesson'])
    # Product bootstrap/spec may precede feature selection, never imply scope approval.
    unscoped = (has_lesson and s['lesson']['phase'] in ('bootstrap', 'spec')
                and s['stage'] in (s['lesson']['phase'], 'paused') and s['lesson']['workstream'] == ''
                and s['feature'] == '' and s['scope_confirmation'] == '')
    for key in ('summary', 'next_action') + (() if unscoped else ('feature', 'scope_confirmation')):
        text(s[key])
    for key in ('environment', 'structure', 'desired_change', 'change_confirmation'):
        require(isinstance(s[key], str) and len(s[key]) <= 8000, '문자열 필요: ' + key)
    require(s['stage'] in STAGES, '알 수 없는 단계')
    require(isinstance(s['blockers'], list) and len(s['blockers']) <= 100, 'blockers 목록 필요')
    for b in s['blockers']:
        text(b)
    require(isinstance(s['evidence'], list) and len(s['evidence']) <= MAX_FILES, 'evidence 목록 필요')
    for e in s['evidence']:
        keys(e, ('kind', 'command', 'input', 'expected', 'observed', 'exit_code', 'outcome', 'path', 'sha256'))
        require(e['kind'] in KINDS and e['outcome'] in ('pass', 'fail', 'blocked'), '증거 종류/결과 오류')
        for key in ('command', 'input', 'expected', 'observed'):
            text(e[key])
        relative(e['path'])
        require(type(e['exit_code']) is int or e['exit_code'] is None, 'exit_code 정수/null 필요')
        require(isinstance(e['sha256'], str) and re.fullmatch('[a-f0-9]{64}', e['sha256']), '증거 SHA-256 필요')


def evidence_check(s, project):
    findings = []
    for e in s['evidence']:
        try:
            data = stable_read(project_file(project, e['path']), MAX_FILE)
            require(sha(data) == e['sha256'], '증거 파일 변경')
        except (OSError, ValueError, PlanError) as exc:
            findings.append({'path': e['path'], 'error': str(exc)})
    return findings


def ready(s, findings):
    # Latest evidence per kind wins: a later failure must not be masked by an old pass.
    latest = {e['kind']: e for e in s['evidence']}
    return (not findings and not s['blockers'] and bool(s['feature'].strip())
            and bool(s['scope_confirmation'].strip()) and bool(s['environment'].strip())
            and bool(s['structure'].strip()) and bool(s['desired_change'].strip())
            and bool(s['change_confirmation'].strip())
            and all(k in latest and latest[k]['outcome'] == 'pass' for k in REQUIRED_KINDS))


def put_new(path, data):
    path = safe_path(path)
    require(not path.exists(), '기존 파일 덮어쓰기 금지')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


class Store:
    def __init__(self, project, task):
        self.project = safe_path(project)
        self.folder = safe_path(self.project / '.sparker-implementation' / ident(task))

    def load(self):
        require(self.folder.is_dir(), '구현 기록 없음')
        paths = sorted(self.folder.glob('r*.json'))
        require(bool(paths), '구현 기록 없음')
        previous = None
        for number, path in enumerate(paths, 1):
            require(path.name == 'r%06d.json' % number, '리비전 누락/이름 오류')
            r = parse(stable_read(path, MAX_FILE))
            keys(r, ('version', 'revision', 'previous', 'source', 'state'))
            require(type(r['version']) is int and r['version'] == 1 and type(r['revision']) is int
                    and r['revision'] == number and r['previous'] == previous, '기록 체인 오류')
            validate_state(r['state'])
            previous = digest(r)
        return r

    def save(self, state, expected=None, source=None):
        validate_state(state)
        self.folder.mkdir(parents=True, exist_ok=True)
        lock = safe_path(self.folder / '.lock')
        lock.mkdir()  # Never remove a lock we did not acquire.
        try:
            if expected is None:
                require(not list(self.folder.glob('r*.json')), '이미 존재하는 과제')
                require(source is not None, '기획 출처 필요')
                r = {'version': 1, 'revision': 1, 'previous': None, 'source': source, 'state': state}
            else:
                old = self.load()
                require(type(expected) is int and old['revision'] == expected, '오래된 리비전')
                require(state['evidence'][:len(old['state']['evidence'])] == old['state']['evidence'], '기존 증거 수정/삭제 금지; 새 결과를 추가하세요')
                r = dict(old, revision=expected + 1, previous=digest(old), state=state)
            require(not evidence_check(state, self.project), '증거 파일 누락/변경')
            data = (canonical(r) + '\n').encode('utf-8')
            require(len(data) <= MAX_FILE, '기록 크기 초과')
            # Incomplete writes are never visible as revisions.
            pending = self.folder / '.pending.json'
            put_new(pending, data)
            require(parse(stable_read(pending, MAX_FILE)) == r, '저장 검증 실패')
            pending.rename(self.folder / ('r%06d.json' % r['revision']))
            return r
        finally:
            lock.rmdir()

    def show(self):
        r = self.load()
        findings = evidence_check(r['state'], self.project)
        return dict(r, evidence_findings=findings, ready_for_local_package=bool(ready(r['state'], findings)))


def report(r):
    s = r['state']
    lines = ['# 2주차 구현 기록', '', '로컬 기록이며 사람 발화·실행 진위를 인증하지 않습니다. 업로드/업무 효과 증거가 아닙니다.', '',
             '## 기획 요약', s['summary'], '## 오늘의 기능', s['feature'],
             '## 환경', s['environment'], '## 구조', s['structure'],
             '## 선택한 변경', s['desired_change'], '## 실행과 시험']
    for e in s['evidence']:
        lines += ['- %s: %s — %s' % (e['kind'], e['outcome'], e['observed']),
                  '  - 명령: ' + e['command'], '  - 입력: ' + e['input'], '  - 기대: ' + e['expected'],
                  '  - 증거: ' + e['path'] + ' (SHA-256 ' + e['sha256'] + ')']
    lines += ['## 막힌 점'] + s['blockers'] + ['## 다음 행동', s['next_action']]
    if 'lesson' in s:
        lesson = s['lesson']
        lines += ['## 학습 진행', '단계: ' + lesson['phase'], '대기 대상: ' + lesson['waiting_for'],
                  '제품 경로: ' + lesson['product_path'], '로컬 URL: ' + lesson['local_url'],
                  '작업 흐름: ' + lesson['workstream'], '### 수용 기준']
        lines += ['- ' + criterion for criterion in lesson['acceptance_criteria']]
        lines += ['### 학습자 관찰', lesson['learner_observation']]
    return ('\n\n'.join(lines) + '\n').encode('utf-8')


def package(store, names, output):
    r = store.load()
    require(ready(r['state'], evidence_check(r['state'], store.project)), '환경/실행/변경/정상·예외·두번째 입력의 실제 증거와 설명 필요')
    require(isinstance(names, list) and 0 < len(names) <= MAX_FILES, '명시적 파일 목록 필요')
    files = {}
    folded = set()
    for name in names:
        relative(name)
        require(name.casefold() not in folded and name.casefold() not in ('implementation.md', 'manifest.json'), '중복/예약 제출 경로')
        folded.add(name.casefold())
        data = stable_read(project_file(store.project, name), MAX_FILE)
        allowed(name, data)
        files[name] = data
    require(any(PurePosixPath(n).name.lower() == 'readme.md' for n in files), '실행 방법 README.md 필요')
    require(any(PurePosixPath(n).suffix.lower() not in ('.md', '.txt', '.csv', '.json') for n in files), '선택한 구현 코드 필요')
    require(all(e['path'] in files for e in r['state']['evidence']), '기록된 실행/시험 증거를 파일 목록에 명시하세요')
    files['implementation.md'] = report(r)
    allowed('implementation.md', files['implementation.md'])
    require(sum(map(len, files.values())) <= MAX_TOTAL, '제출 총 크기 한도')
    manifest = {'format': 'sparker-week2-local-v1', 'state': 'prepared_locally_not_submitted',
                'week': 2, 'record_sha256': digest(r), 'files': {n: sha(d) for n, d in sorted(files.items())}}
    files['manifest.json'] = (canonical(manifest) + '\n').encode('utf-8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    put_new(output, buf.getvalue())
    return {'path': str(safe_path(output)), 'sha256': sha(buf.getvalue()), **manifest}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', default='.', help='승인한 개인 실습 폴더 (기록/증거의 기준)')
    sub = p.add_subparsers(dest='action', required=True)
    i = sub.add_parser('intake', help='MD 읽기 / PDF 호스트 읽기 필요 표시 / ZIP 안전 검사')
    i.add_argument('path'); i.add_argument('--member', help='ZIP 내부의 명시한 MD/PDF 경로')
    for action in ('new', 'show', 'update', 'export', 'package'):
        q = sub.add_parser(action, help={'new': '기획 출처와 별도 구현 기록 생성', 'show': '최신 기록 재개·증거 파일 재검사', 'update': '기존 기록 보존, 새 리비전 저장', 'export': '한국어 구현 기록 MD 내보내기', 'package': '명시한 코드/README/시험 증거만 로컬 ZIP 준비'}[action])
        q.add_argument('task', help='도우미 내부 과제 식별자')
        if action in ('new', 'update'):
            q.add_argument('--input', required=True, help='문서의 state 스키마를 따른 JSON 파일')
        if action == 'new':
            q.add_argument('--plan', required=True, help='원본 MD/PDF/ZIP; 수정하지 않음')
            q.add_argument('--member'); q.add_argument('--read-note', help='PDF를 실제 읽은 호스트 도구·페이지 범위 기록; OCR 미지원이면 생성 중단')
        if action == 'update':
            q.add_argument('--expected-revision', required=True, type=int)
        if action in ('export', 'package'):
            q.add_argument('--output', required=True, help='아직 존재하지 않는 출력 경로')
        if action == 'package':
            q.add_argument('--files', required=True, help='프로젝트 상대 파일 경로 문자열 배열 JSON. 디렉터리/자동 탐색 불가')
    a = p.parse_args(argv)
    try:
        if a.action == 'intake':
            result = intake(a.path, a.member)
        else:
            store = Store(a.project, a.task)
            if a.action == 'new':
                src = intake(a.plan, a.member)
                require(src['status'] != 'choose_member', 'ZIP 내부 기획서를 --member로 선택하세요')
                if src['status'] == 'needs_host_read':
                    text(a.read_note)
                src.pop('text', None)
                src['read_note'] = a.read_note or 'MD UTF-8 읽기'
                result = store.save(parse(stable_read(a.input, MAX_FILE)), source=src)
            elif a.action == 'update':
                result = store.save(parse(stable_read(a.input, MAX_FILE)), expected=a.expected_revision)
            elif a.action == 'show':
                result = store.show()
            elif a.action == 'export':
                put_new(a.output, report(store.load()))
                result = {'path': str(safe_path(a.output)), 'state': 'local_report_only'}
            else:
                result = package(store, parse(stable_read(a.files, MAX_FILE)), a.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PlanError, ValueError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    configure_stdio()
    sys.exit(main())
