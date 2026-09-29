#!/usr/bin/env python3
"""Week 3 local learning ledger. Records evidence; never connects, runs a product or sends."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

from plan import PlanError, canonical, digest, ident, require, safe_path
from implementation import (MAX_FILE, allowed, keys, parse, project_file,
                            put_new, text)
from camp_submit import stable_read, sha
from portable import configure_stdio

CRITERIA = ('쓸 이유', '자료와 권한', '결과 신뢰성', '이용 가능성', '업무 연결', '지속 사용')
JUDGMENTS = ('확인됨', '부족함', '아직 모름')
STEPS = ('input_read', 'product_use', 'output_approval', 'output_sent', 'output_received')
DESIGN = ('trigger', 'source', 'input', 'processing', 'human_decision', 'output',
          'recipient', 'next_action', 'failure_recovery', 'change_consent')


def clean(value):
    """Fail closed for known secret forms; do not retain raw source/tool responses."""
    data = (value if isinstance(value, str) else canonical(value)).encode('utf-8')
    require(len(data) <= MAX_FILE, '기록 크기 초과')
    allowed('week3.json', data)
    # The shared export scanner covers provider keys; cover credential assignments
    # and authenticated URLs in learning notes as well. Never echo rejected values.
    pattern = r'(?i)(?:[\"\s]|^)(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|cookie|client[_-]?secret)\s*[\"]?\s*[:=]\s*[\"]?[^\s\",}]+'
    require(not re.search(pattern, data.decode('utf-8')), '자격 증명 의심 내용 금지')
    require(not re.search(r'(?i)bearer\s+\S+|https?://[^/\s]+@|[?&](?:token|key|sig|signature|code)=', data.decode('utf-8')), '인증값/서명 URL 금지')


def strings(obj, names):
    for name in names:
        text(obj[name])


def initial(source):
    keys(source, ('summary', 'plan_ref', 'product_ref'))
    strings(source, source)
    return {'source': source, 'before': {}, 'after': {}, 'design': None,
            'runs': [], 'current': None, 'steps': {}, 'finished': False,
            'blocked': '', 'next_action': '기존 기획·코드를 읽고 여섯 기준 평가', 'phase': 'evaluate_design'}


def chain_complete(s):
    return all(k in s['steps'] for k in STEPS) and not s['blocked']


def apply(s, event):
    """Pure replay validation: an event cannot imply unobserved later milestones."""
    clean(event)
    require(isinstance(event, dict) and 'kind' in event, 'kind 필요')
    kind = event['kind']
    if kind == 'assessment':
        keys(event, ('kind', 'when', 'criterion', 'judgment', 'evidence', 'next_action'))
        require(event['when'] in ('before', 'after'), 'before/after 필요')
        require(event['criterion'] in CRITERIA and event['judgment'] in JUDGMENTS, '평가 기준/판정 오류')
        strings(event, ('evidence', 'next_action'))
        if event['when'] == 'after':
            require(s['design'] is not None, '재평가 전에 설계 필요')
        s[event['when']][event['criterion']] = event
        s['finished'] = False
    elif kind == 'design':
        keys(event, ('kind',) + DESIGN)
        strings(event, DESIGN)
        require(len(s['before']) == 6, '설계 전에 여섯 기준 평가 필요')
        require(s['current'] is None, '실행 시작 후 설계 변경은 별도 과제에서 기록')
        s['design'] = event
        s['after'] = {}
        s['phase'] = 'input_integration'
    elif kind in STEPS:
        require(s['design'] is not None, '합의한 설계 필요')
        base = ('kind', 'run', 'mode')
        if kind == 'output_approval':
            keys(event, base + ('recipient', 'content_sha256', 'consent'))
            strings(event, ('recipient', 'consent'))
        else:
            fields = ('artifact', 'sha256', 'observation')
            if kind == 'product_use':
                fields += ('input_sha256',)
            if kind in ('output_sent', 'output_received'):
                fields += ('recipient', 'content_sha256')
            keys(event, base + fields)
            strings(event, ('artifact', 'observation'))
            # Validate even before project_file() is called during save/check.
            project_file(Path('.'), event['artifact'])
            require(bool(re.fullmatch('[a-f0-9]{64}', event['sha256'])), '증거 SHA-256 필요')
        ident(event['run'])
        require(event['mode'] in ('live', 'local_rehearsal'), 'live/local_rehearsal 구분 필요')
        if kind == 'input_read':
            require(event['run'] not in s['runs'], '새 입력 실행은 새 run 식별자 필요')
            s['runs'].append(event['run'])
            s['current'] = {'run': event['run'], 'mode': event['mode']}
            s['steps'] = {}
            s['after'] = {}
        else:
            require(s['current'] == {'run': event['run'], 'mode': event['mode']}, '같은 run/모드의 증거 필요')
            index = STEPS.index(kind)
            require(list(s['steps']) == list(STEPS[:index]), '선행 단계 필요 또는 중복 기록; 재실행은 새 run으로 시작')
        if kind == 'product_use':
            require(event['input_sha256'] == s['steps']['input_read']['sha256'], '읽은 입력과 제품이 사용한 입력 불일치')
        if kind == 'output_approval':
            require(event['content_sha256'] == s['steps']['product_use']['sha256'], '승인 내용과 제품 출력 불일치')
            require(event['recipient'] == s['design']['recipient'], '설계한 수신처와 불일치')
        if kind in ('output_sent', 'output_received'):
            approval = s['steps']['output_approval']
            require(all(event[k] == approval[k] for k in ('recipient', 'content_sha256')), '승인한 수신처/내용과 불일치')
        if kind == 'output_received':
            sent = s['steps']['output_sent']
            require(event['artifact'] != sent['artifact'] and event['sha256'] != sent['sha256'], '발신 영수증을 수신 증거로 재사용할 수 없음')
        s['steps'][kind] = event
        # Reassessment must describe the latest observation, not an earlier run stage.
        s['after'] = {}
        s['blocked'] = ''
        s['finished'] = False
        s['phase'] = 'input_integration' if kind == 'input_read' else 'output_integration'
    elif kind == 'pause':
        keys(event, ('kind', 'blocker', 'next_action'))
        strings(event, ('blocker', 'next_action'))
        s['blocked'] = event['blocker']
        s['next_action'] = event['next_action']
        s['finished'] = False
    elif kind == 'finish':
        keys(event, ('kind', 'consent', 'next_action'))
        strings(event, ('consent', 'next_action'))
        require(chain_complete(s) and len(s['after']) == 6, '읽기·제품 사용·승인·발신·수신 및 여섯 기준 재평가 필요')
        s['finished'] = True
        s['next_action'] = event['next_action']
        s['phase'] = 'reviewed'
    else:
        raise PlanError('알 수 없는 이벤트')
    if kind not in ('pause', 'finish'):
        if not s['design']:
            s['next_action'] = '여섯 기준 평가 후 입력→처리→사람 판단→출력 설계'
        else:
            missing = [k for k in STEPS if k not in s['steps']]
            s['next_action'] = ('다음 증거: ' + missing[0]) if missing else '여섯 기준 재평가·참가자 확인 (운영 성공 선언 아님)'
    return s


def evidence_findings(s, project):
    findings = []
    for event in s['steps'].values():
        if 'artifact' not in event:
            continue
        try:
            data = stable_read(project_file(project, event['artifact']), MAX_FILE)
            allowed(event['artifact'], data)
            clean(data.decode('utf-8-sig'))
            require(sha(data) == event['sha256'], '증거 파일 변경')
        except (OSError, ValueError, PlanError):
            findings.append({'kind': event['kind'], 'error': '증거 누락/변경/비허용 내용'})
    return findings


class Store:
    def __init__(self, project, task):
        self.project = safe_path(project)
        self.folder = safe_path(self.project / '.sparker-week3' / ident(task))

    def load(self):
        paths = sorted(self.folder.glob('r*.json'))
        require(bool(paths), '3주차 기록 없음')
        previous, state = None, None
        for number, path in enumerate(paths, 1):
            require(path.name == 'r%06d.json' % number, '리비전 누락/이름 오류')
            record = parse(stable_read(safe_path(path), MAX_FILE))
            clean(record)
            keys(record, ('version', 'revision', 'previous', 'source', 'event'))
            require(type(record['version']) is int and record['version'] == 1
                    and type(record['revision']) is int and record['revision'] == number
                    and record['previous'] == previous, '기록 체인 오류')
            if state is None:
                require(record['event'] is None, '첫 기록은 출처만 허용')
                state = initial(record['source'])
            else:
                require(record['source'] == state['source'], '기획 출처 변경 금지')
                apply(state, record['event'])
            previous = digest(record)
        return record, state

    def write(self, source=None, event=None, expected=None):
        # Source/event safety checks run before creating a ledger directory.
        clean(source if expected is None else event)
        self.folder.mkdir(parents=True, exist_ok=True)
        lock = safe_path(self.folder / '.lock')
        lock.mkdir()
        try:
            if expected is None:
                require(not list(self.folder.glob('r*.json')), '이미 존재하는 과제')
                state = initial(source)
                record = dict(version=1, revision=1, previous=None, source=source, event=None)
            else:
                old, state = self.load()
                require(old['revision'] == expected, '오래된 리비전; show 후 재개')
                apply(state, event)
                require(not evidence_findings(state, self.project), '증거 파일 누락/변경/비허용 내용')
                record = dict(version=1, revision=expected + 1, previous=digest(old),
                              source=old['source'], event=copy.deepcopy(event))
            data = (canonical(record) + '\n').encode('utf-8')
            require(len(data) <= MAX_FILE, '기록 크기 초과')
            pending = self.folder / '.pending.json'
            put_new(pending, data)
            require(parse(stable_read(pending, MAX_FILE)) == record, '저장 검증 실패')
            pending.rename(self.folder / ('r%06d.json' % record['revision']))
        finally:
            lock.rmdir()
        return self.show()

    def show(self):
        record, state = self.load()
        findings = evidence_findings(state, self.project)
        mode = state['current']['mode'] if state['current'] else 'not_run'
        return {'revision': record['revision'], 'record_sha256': digest(record), 'state': state,
                'evidence_findings': findings, 'mode': mode,
                'evidence_chain_complete': bool(chain_complete(state) and not findings),
                'learning_review_complete': bool(state['finished'] and not findings),
                'production_readiness': 'not_certified',
                'notice': '자기보고 로컬 기록: CLI는 실행·동의·수신의 진위를 인증하지 않습니다. local_rehearsal은 운영 연결 성공이 아닙니다.'}


def report(result):
    s = result['state']
    lines = ['# 3주차 평가·연결 기록', result['notice'],
             '모드: ' + result['mode'], '단계: ' + s['phase'],
             '학습 검토 완료: ' + str(result['learning_review_complete']),
             '입력→수신 증거 체인: ' + str(result['evidence_chain_complete']),
             '운영 준비 판정: 미인증 / 업로드하지 않음', '## 기존 업무', s['source']['summary'],
             '기획 참조: ' + s['source']['plan_ref'], '제품 참조: ' + s['source']['product_ref']]
    for when, label in (('before', '변경 전 평가'), ('after', '연결 후 재평가')):
        lines.append('## ' + label)
        for criterion in CRITERIA:
            a = s[when].get(criterion)
            lines.append('- ' + criterion + ': ' + (a['judgment'] + ' — ' + a['evidence'] + ' / 다음: ' + a['next_action'] if a else '미평가'))
    lines.append('## 합의한 구조 (원본 기획·제품 덮어쓰기 아님)')
    if s['design']:
        lines.extend('- ' + k + ': ' + s['design'][k] for k in DESIGN)
    else:
        lines.append('미설계')
    lines.append('## 현재 실행 증거 (원문 파일은 내보내지 않음)')
    for k in STEPS:
        e = s['steps'].get(k)
        lines.append('- ' + k + ': ' + (canonical(e) if e else '미확인'))
    lines.extend(['## 증거 재검사', canonical(result['evidence_findings']),
                  '## 막힌 점', s['blocked'] or '기록 없음 (문제 없음의 증명 아님)',
                  '## 이어갈 행동', s['next_action']])
    data = ('\n\n'.join(lines) + '\n').encode('utf-8')
    clean(data.decode('utf-8'))
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.', help='기존 개인 실습 폴더; 쓰기는 .sparker-week3 별도 기록')
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('new', 'show', 'append', 'export'):
        p = sub.add_parser(action)
        p.add_argument('task')
        if action in ('new', 'append'):
            p.add_argument('--input', required=True, help='new: 출처 JSON / append: 이벤트 JSON. 비밀·원문 금지')
        if action == 'append':
            p.add_argument('--expected-revision', type=int, required=True)
        if action == 'export':
            p.add_argument('--output', required=True, help='미완료도 가능; 기존 파일 덮어쓰기 금지')
    a = parser.parse_args(argv)
    try:
        store = Store(a.project, a.task)
        if a.action == 'new':
            result = store.write(source=parse(stable_read(safe_path(a.input), MAX_FILE)))
        elif a.action == 'append':
            result = store.write(event=parse(stable_read(safe_path(a.input), MAX_FILE)), expected=a.expected_revision)
        elif a.action == 'show':
            result = store.show()
        else:
            data = report(store.show())
            put_new(a.output, data)
            result = {'path': str(safe_path(a.output)), 'sha256': sha(data), 'status': 'local_report_only_not_submitted'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PlanError, OSError, ValueError, TypeError, KeyError):
        # Avoid accidentally echoing credentials from malformed JSON/provider logs.
        print(json.dumps({'error': '기록 거절: 스키마·선행 단계·리비전·증거 경로/해시·비밀 포함 여부를 확인하세요.'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    configure_stdio()
    sys.exit(main())
