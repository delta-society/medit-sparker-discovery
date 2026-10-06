#!/usr/bin/env python3
"""Sparker W4: local evidence gates, revision-bound one-page PDF and code bundle.
No transcript instruction execution, network access, or transcription service.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import zipfile
from io import BytesIO

from plan import require, safe_path, digest
from pdf_browser import print_pdf
import evaluation

MAX_BUNDLE = 5 * 1024 * 1024  # existing submission storage ceiling
BLOCKED = {'.git', '.env', '.ssh', '.aws', '.config', 'node_modules', '__pycache__',
           '.sparker-week4', '.sparker-evaluation', 'credentials', 'secrets'}
SECRET = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})|(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[=:]\s*[\x22\x27]?[A-Za-z0-9_+/=-]{12,}', re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(v, maximum=800):
    require(isinstance(v, str) and bool(v.strip()) and len(v) <= maximum, '빈 문장/길이 한도 오류')


def read(p):
    p = safe_path(Path(p))
    require(p.stat().st_size < 2_000_000, '기록 크기 초과')
    return json.loads(p.read_text(encoding='utf-8'))


def files(root, names):
    root = safe_path(Path(root).absolute())
    require(isinstance(names, list) and bool(names) and len(names) == len(set(names)), '명시 소스 목록 필요')
    result = {}
    for name in sorted(names):
        p = Path(name)
        require(not p.is_absolute() and '..' not in p.parts and '\\' not in name, '상대 경로만 허용')
        require(not any(x.lower() in BLOCKED or x.lower().startswith('.env') for x in p.parts), '인증/작업/의존 캐시 제외')
        require(not re.search(r'(credential|secret|token|id_rsa|\.pem$|\.key$|\.p12$|\.zip$|\.sqlite$)', name, re.I), '민감/중첩 압축 파일 제외')
        f = safe_path(root / p)
        require(f.is_file() and f.stat().st_size <= MAX_BUNDLE, '일반 소스 파일만 허용')
        data = f.read_bytes()
        require(not SECRET.search(data), '자격증명 의심 내용: 제거 후 재시도')
        result[name] = data
    require(sum(map(len, result.values())) <= MAX_BUNDLE, '소스 크기 초과')
    return result


def manifest(data):
    return {k: sha(v) for k, v in sorted(data.items())}


def load(root):
    records = sorted(Path(root).glob('r*.json'))
    require(bool(records), 'W4 기록 없음')
    previous = None
    for i, p in enumerate(records, 1):
        r = read(p)
        require(p.name == 'r%06d.json' % i and r['revision'] == i and r['previous'] == previous,
                '리비전 연결 오류')
        require(r['digest'] == digest(r['document']), '기록 무결성 오류')
        previous = digest(r)
    return r


def save(root, doc):
    root = safe_path(Path(root).absolute()); root.mkdir(parents=True, exist_ok=True)
    lock = root / '.lock'; lock.mkdir()
    try:
        old = load(root) if list(root.glob('r*.json')) else None
        r = dict(revision=old['revision'] + 1 if old else 1, previous=digest(old) if old else None,
                 digest=digest(doc), document=doc)
        with (root / ('r%06d.json' % r['revision'])).open('x', encoding='utf-8') as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        return r
    finally:
        lock.rmdir()


def source(path):
    p = safe_path(Path(path).absolute()); raw = p.read_bytes()
    require(len(raw) <= 2_000_000, '전사/기획 크기 초과')
    return dict(path=str(p), sha256=sha(raw))


def cite(sources, c):
    require(isinstance(c, dict) and c.get('source') in sources, '출처 ID 필요')
    s = sources[c['source']]; raw = safe_path(Path(s['path'])).read_bytes()
    require(sha(raw) == s['sha256'], '원문 변경: 근거 재검토 필요')
    lines = raw.decode('utf-8-sig').splitlines()
    a, b = c.get('line_start'), c.get('line_end')
    require(type(a) is int and type(b) is int and 1 <= a <= b <= len(lines), '원문 행 범위 오류')
    text(c.get('quote'), 1500)
    excerpt = '\n'.join(lines[a-1:b])
    require(c['quote'] in excerpt, '인용문/원문 위치 불일치')
    if c.get('timestamp'):
        require(c['timestamp'] in excerpt, '타임스탬프/원문 불일치')
    return c


def initialize(root, spec):
    require(not list(Path(root).glob('r*.json')), '기존 기록 덮어쓰기 금지')
    text(spec['product']); text(spec['title'], 80)
    data = files(spec['code_root'], spec['files'])
    require(any(Path(n).name.lower().startswith('readme') for n in data), '실행 안내 README 필요')
    text(spec['dependency_note'])
    sources = {k: source(v) for k, v in spec['sources'].items()}
    require(sources and spec['principles'], '기존 기획/코드 출처와 원칙 후보 필요')
    ids = set()
    for p in spec['principles']:
        text(p['id']); text(p['text']); require(p['id'] not in ids, '원칙 ID 중복'); ids.add(p['id'])
        cite(sources, p['evidence'])
    doc = dict(spec, sources=sources, baseline=manifest(data), phase='principles_draft', feedback=[],
               principle_confirmation=None, selection_confirmation=None, final=None)
    return save(root, doc)


def confirm_principles(root, expected, statement):
    r = load(root); d = copy.deepcopy(r['document'])
    require(r['digest'] == expected and d['phase'] == 'principles_draft', '보여준 원칙과 현재 상태 확인')
    text(statement)
    for p in d['principles']: cite(d['sources'], p['evidence'])
    d.update(phase='review', principle_confirmation=statement, principles_digest=digest(d['principles']))
    return save(root, d)


def review(root, rows):
    d = copy.deepcopy(load(root)['document'])
    require(d['phase'] == 'review', '원칙 확인 후/선택 전만 피드백 수정 가능')
    ids = set(); principles = {p['id'] for p in d['principles']}
    for f in rows:
        text(f['id']); require(f['id'] not in ids, '피드백 ID 중복'); ids.add(f['id'])
        require(f['product'] == d['product'], '혼합 인터뷰: 대상 제품을 먼저 구분하세요')
        cite(d['sources'], f['evidence'])
        require(f['speaker_certainty'] in ('confirmed', 'uncertain', 'unknown'), '화자 불확실성 필요')
        text(f['speaker']); text(f['need']); text(f['request']); text(f['reason']); text(f['expected']); text(f['keep'])
        require(f['fit'] in ('fit', 'conflict', 'insufficient'), '부합/충돌/정보 부족 분류 필요')
        require(isinstance(f['principles'], list) and set(f['principles']) <= principles and bool(f['principles']), '관련 원칙 ID 필요')
        require(isinstance(f['paths'], list) and f['paths'], '수정 후보 파일 범위 필요')
    require(bool(rows), '전사 근거 피드백 필요')
    d['feedback'] = rows
    return save(root, d)


def select(root, expected, choices, statement):
    r = load(root); d = copy.deepcopy(r['document']); text(statement)
    require(r['digest'] == expected and d['phase'] == 'review' and d['feedback'], '보여준 피드백 최신본 선택 필요')
    require(set(choices) == {f['id'] for f in d['feedback']}, '모든 후보에 반영/보류 판단 필요')
    for f in d['feedback']:
        choice = choices[f['id']]
        require(choice['decision'] in ('apply', 'defer'), '반영/보류 오류'); text(choice['reason'])
        require(choice['decision'] != 'apply' or (f['fit'] == 'fit' and f['speaker_certainty'] == 'confirmed'),
                '충돌/정보 부족/화자 불확실 항목은 확인 후 다시 분류하세요. 원칙 자동 변경 금지')
        f['choice'] = choice
    require(manifest(files(d['code_root'], d['files'])) == d['baseline'], '참가자 선택 전에 코드가 변경됨')
    d.update(phase='selected', selection_confirmation=statement)
    return save(root, d)


def final(root, result):
    d = copy.deepcopy(load(root)['document'])
    require(d['phase'] in ('selected', 'final_draft', 'confirmed'), '참가자 선택 전 수정 결과 기록 금지')
    require(digest(d['principles']) == d['principles_digest'], '대원칙 변경 금지: 별도 확인 과정 필요')
    data = files(d['code_root'], result['files']); current = manifest(data)
    changed = {k for k in set(current) | set(d['baseline']) if current.get(k) != d['baseline'].get(k)}
    allowed = {p for f in d['feedback'] if f['choice']['decision'] == 'apply' for p in f['paths']}
    require(changed <= allowed, '선택 범위 밖 코드 변경')
    for k in ('summary', 'before', 'after', 'remaining'): text(result[k], 650)
    require(result['tests'], '최종 시험 근거 필요')
    for t in result['tests']:
        text(t['command']); require(t['code_digest'] == digest(current), '다른 코드 버전 시험 기록')
        require(type(t['exit_code']) is int, '실제 시험 종료 코드 필요')
        s = source(t['log']); require(s['sha256'] == t['sha256'], '시험 로그 해시 불일치')
    peer = result['peer']; require(peer['status'] in ('checked', 'not_checked'), '동료 재확인 상태 필요')
    text(peer['remaining'])
    if peer['status'] == 'checked':
        text(peer['reviewer']); require(peer['same_peer'] is True, '같은 짝인지 확인 필요')
        require(re.fullmatch('[a-f0-9]{64}', peer['code_digest']) is not None, '재확인 대상 코드 digest 필요')
        s = source(peer['source']); cite({'peer': s}, peer['evidence']); peer['source_receipt'] = s
        peer['matches_final'] = peer['code_digest'] == digest(current)
    else:
        peer['matches_final'] = False
    d.update(phase='final_draft', final=dict(result, code=current, code_digest=digest(current)), report_confirmation=None)
    return save(root, d)


def verify(d):
    require(digest(d['principles']) == d['principles_digest'], '원칙 변경 감지')
    for p in d['principles']: cite(d['sources'], p['evidence'])
    for f in d['feedback']: cite(d['sources'], f['evidence'])
    current = files(d['code_root'], d['final']['files'])
    require(manifest(current) == d['final']['code'], '최종 기록 후 코드 변경: 시험/보고서 재확인 필요')
    for t in d['final']['tests']: require(source(t['log'])['sha256'] == t['sha256'], '시험 로그 변경')
    peer = d['final']['peer']
    if peer['status'] == 'checked': cite({'peer': peer['source_receipt']}, peer['evidence'])
    return current


def confirm(root, expected, statement):
    r = load(root); d = copy.deepcopy(r['document']); text(statement)
    require(r['digest'] == expected and d['phase'] == 'final_draft', '최종 코드/보고서 초안 재검토 필요')
    verify(d); d.update(phase='confirmed', report_confirmation=statement)
    return save(root, d)


def document(r):
    d = r['document']; f = d['final']; e = lambda s: html.escape(str(s), quote=True)
    rows = ''.join('<li><b>'+e(x['evidence']['quote'])+'</b> ('+e(x['evidence']['source'])+' L'+str(x['evidence']['line_start'])+' / '+e(x['speaker'])+' '+e(x['speaker_certainty'])+')<br>'+e(x['fit'])+' · '+e('; '.join(p['text'] for p in d['principles'] if p['id'] in x['principles']))+' · '+e(x['choice']['decision'])+' — '+e(x['choice']['reason'])+'</li>' for x in d['feedback'])
    peer = f['peer']; peertext = '동료 재확인 미실시'
    if peer['status'] == 'checked':
        peertext = peer['evidence']['quote'] + (' · 최종 코드 확인' if peer['matches_final'] else ' · 이전 코드 확인; 최종 재수정본은 동료 미확인')
    css = (Path(__file__).resolve().parents[1]/'assets/pdf/fonts.css').read_text(encoding='utf-8')
    body = '<header>SPARKER · WEEK 4 · '+e(d['title'])+'</header><h1>피드백 반영 결과</h1><h2>받은 피드백 · 원칙에 따른 판단</h2><ul>'+rows+'</ul><h2>반영한 내용 · 전후 시험</h2><p>'+e(f['summary'])+'</p><p>전: '+e(f['before'])+'<br>후: '+e(f['after'])+'</p><p>시험: '+e('; '.join(t['command']+' → exit '+str(t['exit_code']) for t in f['tests']))+'</p><h2>같은 동료의 재확인 · 남은 문제</h2><p>'+e(peertext)+'</p><p>'+e(peer['remaining'])+' / '+e(f['remaining'])+'</p><footer>최종 코드 SHA256 '+e(f['code_digest'])+'<br>기록 '+e(r['digest'])+'<br>동료의 부서 관점 확인이며 업무 인수·실사용·효과 실측이 아닙니다.</footer>'
    style = '@page{size:A4;margin:15mm}*{box-sizing:border-box}body{width:180mm;margin:0;font-family:"Noto Sans KR Variable",sans-serif;font-size:10pt;line-height:1.5;overflow-wrap:anywhere;color:#182934}header{color:#176052;border-bottom:2px solid;padding:8px 0}h1{font-size:22pt}h2{font-size:13pt;margin-top:18px}li{margin:8px 0}footer{font-size:7pt;margin-top:16px;border-top:1px solid #bbb;padding-top:8px}'
    js = 'window.__sparkerPdfReady=(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(r));let h=document.body.getBoundingClientRect().height;let w=document.documentElement.scrollWidth;return {ok:h<=1000&&w<=794,code:h>1000?"layout":null,height:h,width:w,one_page:true};})();'
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; font-src data:; connect-src \'none\'"><style>'+css+style+'</style><body>'+body+'<script>'+js+'</script></body></html>'


def bundle(root):
    root = Path(root); r = load(root); d = r['document']
    require(d['phase'] == 'confirmed', '참가자 최종 코드/보고서 확인 필요')
    data = verify(d); rendered = document(r); pdf, observation = print_pdf(rendered, '<span></span>')
    require(pdf.startswith(b'%PDF-'), 'PDF 렌더 실패')
    require(load(root) == r and manifest(verify(d)) == d['final']['code'], '렌더 중 코드/기록 변경')
    out = root / ('bundle-r%06d' % r['revision']); require(not out.exists(), '기존 묶음 덮어쓰기 금지')
    public = dict(format='sparker-week4-feedback-v1', week=4, revision=r['revision'], record_digest=r['digest'], code_digest=d['final']['code_digest'],
                  code=d['final']['code'], report_sha256=sha(pdf), peer_matches_final=d['final']['peer']['matches_final'])
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, raw in data.items(): z.writestr('code/'+name, raw)
        z.writestr('report.pdf', pdf); z.writestr('manifest.json', json.dumps(public, ensure_ascii=False, indent=2))
    raw = buf.getvalue(); require(len(raw) <= MAX_BUNDLE, '제출 묶음 5MiB 초과')
    out.mkdir(); (out/'final-code-and-report.zip').write_bytes(raw)
    (out/'report.pdf').write_bytes(pdf); (out/'report.html').write_text(rendered, encoding='utf-8')
    receipt = dict(public, sha256=sha(raw), size=len(raw), observation=observation)
    (out/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return receipt


def current_bundle(root):
    r = load(root); d = r['document']; require(d['phase'] == 'confirmed', '최종 확인 필요'); verify(d)
    out = Path(root)/('bundle-r%06d' % r['revision']); receipt = read(out/'receipt.json')
    raw = safe_path(out/'final-code-and-report.zip').read_bytes()
    require(receipt['record_digest'] == r['digest'] and sha(raw) == receipt['sha256'] and len(raw) <= MAX_BUNDLE, '묶음 정합 실패')
    require((out/'report.html').read_text(encoding='utf-8') == document(r), '보고서 원문 변경')
    with zipfile.ZipFile(BytesIO(raw)) as z:
        require(set(z.namelist()) == {'code/'+n for n in d['final']['code']} | {'report.pdf','manifest.json'}, '예상 밖 묶음 항목')
        for n, h in d['final']['code'].items(): require(sha(z.read('code/'+n)) == h, '소스 해시 불일치')
        m = json.loads(z.read('manifest.json'))
        require(m['record_digest'] == r['digest'] and m['code'] == d['final']['code'] and m['code_digest'] == d['final']['code_digest'], 'manifest 불일치')
        require(sha(z.read('report.pdf')) == receipt['report_sha256'] == m['report_sha256'], 'PDF 해시 불일치')
    return r, raw, dict(week=4, filename='final-code-and-report.zip', size=len(raw), sha256=sha(raw))


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['init','principles','review','select','final','confirm','bundle','show','submit'])
    p.add_argument('--root', required=True); p.add_argument('--input'); p.add_argument('--expected'); p.add_argument('--statement')
    p.add_argument('--origin'); p.add_argument('--local-test', action='store_true'); p.add_argument('--submit', action='store_true')
    a = p.parse_args(); root = safe_path(Path(a.root).absolute())
    if a.action == 'init': result = initialize(root, read(a.input))
    elif a.action == 'principles': result = confirm_principles(root, a.expected, a.statement)
    elif a.action == 'review': result = review(root, read(a.input))
    elif a.action == 'select': result = select(root, a.expected, read(a.input), a.statement)
    elif a.action == 'final': result = final(root, read(a.input))
    elif a.action == 'confirm': result = confirm(root, a.expected, a.statement)
    elif a.action == 'bundle': result = bundle(root)
    elif a.action == 'submit':
        import submission_bridge as bridge
        require(a.local_test and a.origin and a.origin != bridge.PRODUCTION, 'W4 서버/권한 확장은 미배포: 현재는 격리 로컬 시험만 허용')
        result = bridge.submit(root, consent=a.submit, base=a.origin, local_test=True, artifact_loader=current_bundle, scope=4)
        if result['status'] == 'expired': result = bridge.submit(root, consent=a.submit, base=a.origin, local_test=True, artifact_loader=current_bundle, scope=4)
    else: result = load(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if a.action != 'submit' or result['status'] == 'submitted' else 2


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status':'blocked', 'message':str(error)}, ensure_ascii=False)); sys.exit(1)
