"""Offline A4 derivative of an immutable, human-finalized plan. Stdlib only."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import tempfile

from plan import PlanError, digest, markdown, read_json, require, safe_path
from pdf_browser import PdfError, print_pdf
from pdf_presentation import hints

ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'pdf'
FORMAT = 1
SCENARIOS = (
    ('reconciliation', '대사·정합성 확인', ('대사', '미수', 'aging', 'citi', '입금')),
    ('consistency', '기준·구현 일치 확인', ('정책', '사양', '규정', 'spec', '코드', 'quickbuild')),
    ('creative', '콘텐츠 제작·검토', ('이미지', '크리에이티브', '디자인', 'creative')),
    ('evidence', '근거 검색·검토', ('유사 사례', '유사사례', '후보자', '소싱', '검색', '측정', '표준시간')),
    ('reporting', '정보 수집·보고', ('보고', '리포트', '뉴스레터', 'newsletter', 'report')),
    ('operations', '업무 전달·실행', ('주문', '발주', 'rfq', 'fta', '납기', '메일', 'sap')),
)


def scenario(plan):
    source = ' '.join([plan['selected_change']['change'], plan['user_result']['result']]).lower()
    for key, title, words in SCENARIOS:
        if any(word in source for word in words):
            return key, title
    return 'generic', '업무 개선 기획'


def assets():
    manifest = read_json(ASSETS / 'manifest.json')
    result = {}
    for name in ['render.js', 'fonts.css', 'print.css', 'THIRD_PARTY_NOTICES.md']:
        raw = safe_path(ASSETS / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == manifest['sha256'][name], 'PDF 번들 무결성 오류')
        result[name] = raw.decode('utf-8')
    return result, digest(manifest)


def make_html(record, bundled):
    """Overview repeats existing fields only. Full canonical Markdown follows it."""
    p = record['plan']
    key, title = scenario(p)
    esc = lambda value: html.escape(str(value), quote=True)
    diagrams, figures = [], []
    nodes = []
    for index, step in enumerate(p['workflow'], 1):
        # Display punctuation prevents source text from becoming Mermaid syntax.
        # Exact original text and full actor names remain in the detailed body.
        action = step['step'][:55] + ('…' if len(step['step']) > 55 else '')
        actor = step['actor'][:30] + ('…' if len(step['actor']) > 30 else '')
        label = f"{index}. {action} · {actor}"
        encoded = ' '.join(label.translate(str.maketrans({'"': '＂', '<': '〈', '>': '〉', '`': '′', '#': '＃', '&': '＆', '\\': '／'})).split())
        nodes.append(f'w{index}["{encoded}"]')
    if nodes:
        diagrams.append({'id': 'workflow', 'source': 'flowchart TD\n' + ' --> '.join(nodes), 'nodes': nodes})
        figures.append('<div id="workflow" class="workflow-diagrams"></div>')
    rows = [('사용자', p['user_result']['user']), ('사용 시점', p['user_result']['use_when']),
            ('선택 이유', p['selected_change']['reason'])]
    # Different scenario lenses highlight existing evidence, never add invented metrics.
    lens = {'reconciliation': ('예외·검증 기준', p['quality_conditions']),
            'consistency': ('일치 판단 기준', p['quality_conditions']),
            'creative': ('사람이 검토할 항목', p['responsibilities']['human']),
            'evidence': ('근거·품질 확인', p['quality_conditions']),
            'reporting': ('보고 품질 기준', p['quality_conditions']),
            'operations': ('사람이 맡을 실행·확인', p['responsibilities']['human']),
            'generic': ('품질 조건', p['quality_conditions'])}[key]
    payload = json.dumps({'markdown': markdown(record), 'diagrams': diagrams, 'presentation': hints(p)}, ensure_ascii=False).replace('<', '\\u003c')
    table = ''.join(f'<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>' for label, value in rows)
    criteria = ''.join(f'<li>{esc(value)}</li>' for value in lens[1]) or '<li>기록된 항목 없음</li>'
    outcome = p['user_result']['result']
    change = p['selected_change']['change']
    same = outcome == change
    summary = ('<p class="note">위 결과와 이번 변경 범위가 동일하게 확정되었습니다.</p>' if same else
               '<div class="summary"><h2>이번에 바꿀 것</h2><p>' + esc(change) + '</p></div>')
    action_rows = ''.join(f'<tr><th>{label}</th><td>{esc(p["next_action"][field])}</td></tr>'
                          for label, field in [('담당', 'owner'), ('할 일', 'action'), ('완료 조건', 'done_when')])
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; font-src data:; img-src data:; '
            'connect-src \'none\'; base-uri \'none\'; form-action \'none\'">'
            '<title>구현 기획서</title><style>' + bundled['fonts.css'] + '\n' + bundled['print.css'] + '</style></head><body>'
            '<header class="masthead"><span class="brand">SPARKER</span><span class="status">기획 확정</span></header>'
            f'<div class="eyebrow">구현 기획서 · {esc(title)}</div><h1 class="title">{esc(outcome)}</h1>'
            f'<div class="subtitle">{esc(record["case_id"])} · 리비전 {record["revision"]} · {esc(record["created_at"][:10])}</div>'
            '<div class="chapter-label">검토 요약</div>'
            f'{summary}<table class="key-values">{table}</table>'
            f'<section class="summary-quality"><h2>{esc(lens[0])}</h2><ul>{criteria}</ul></section>'
            f'<section class="next-action"><h2>다음 행동</h2><table class="key-values">{action_rows}</table></section>'
            '<p class="note">기획 확정은 구현 완료나 효과 측정 완료를 뜻하지 않습니다. 항목별 가설·미확인 상태는 유지됩니다.</p>'
            + ('<section class="workflow-section"><p class="note">기록된 순서대로 이어집니다. 각 단계의 전체 내용과 근거는 상세 기획에서 확인할 수 있습니다.</p>' + ''.join(figures) + '</section>' if figures else '')
            + '<main id="document-body"></main><script id="pdf-data" type="application/json">' + payload
            + '</script><script>' + bundled['render.js'].replace('</script', '<\\/script') + '</script></body></html>')


def export_pdf(store, case, revision):
    """Publish once by fingerprint; a failure never changes the plan ledger."""
    pending = lock = None
    locked = False
    try:
        store.load(case)  # Validate the entire chain before reading an older finalized revision.
        require(type(revision) is int and 1 <= revision <= 999999, 'PDF 대상 리비전 오류')
        record = read_json(store.case_path(case) / f'r{revision:06d}' / 'plan.json')
        require(record['status'] == 'finalized', 'PDF는 사람이 확정한 기획서만 생성합니다')
        bundled, asset_hash = assets()
        fingerprint = digest({'record': digest(record), 'assets': asset_hash, 'format': FORMAT,
                              'exporter': hashlib.sha256(Path(__file__).read_bytes() +
                                                        Path(__file__).with_name('pdf_browser.py').read_bytes() +
                                                        Path(__file__).with_name('pdf_presentation.py').read_bytes()).hexdigest()})
        base = safe_path(store.root / '.pdf-exports' / case / f'r{revision:06d}')
        base.mkdir(parents=True, exist_ok=True)
        lock = safe_path(base / '.lock')
        try:
            lock.mkdir()
            locked = True
        except FileExistsError:
            raise PdfError('busy', '같은 리비전의 PDF 생성이 진행 중입니다. 종료 후 다시 시도하세요.')
        target = safe_path(base / fingerprint)
        if target.exists():
            receipt = read_json(target / 'receipt.json')
            require(receipt['fingerprint'] == fingerprint, 'PDF 영수증 불일치')
            for name in ['plan.pdf', 'plan.html']:
                require(hashlib.sha256(safe_path(target / name).read_bytes()).hexdigest() == receipt['sha256'][name], '기존 PDF 파일 검증 실패; 덮어쓰지 않습니다')
            return {'status': 'ready', 'reused': True, 'path': str(target / 'plan.pdf'), 'revision': revision}
        document = make_html(record, bundled)
        footer = ('<div style="font:8px sans-serif;width:100%;text-align:center;color:#51616c">'
                  + html.escape(case) + f' · r{revision:06d} · '
                  '<span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        pdf, observation = print_pdf(document, footer)
        pending = Path(tempfile.mkdtemp(prefix='.pending-', dir=base))
        (pending / 'plan.pdf').write_bytes(pdf)
        (pending / 'plan.html').write_text(document, encoding='utf-8')
        receipt = {'format': FORMAT, 'fingerprint': fingerprint, 'revision': revision,
                   'record_sha256': digest(record), 'assets_sha256': asset_hash, 'renderer': observation,
                   'sha256': {name: hashlib.sha256((pending / name).read_bytes()).hexdigest()
                              for name in ['plan.pdf', 'plan.html']}}
        (pending / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        require(not target.exists(), 'PDF 덮어쓰기 금지')
        pending.rename(target)
        pending = None
        return {'status': 'ready', 'reused': False, 'path': str(target / 'plan.pdf'), 'revision': revision}
    except (PdfError, PlanError, OSError, ValueError, KeyError, TypeError) as exc:
        return {'status': 'failed', 'revision': revision, 'code': getattr(exc, 'code', 'export_failed'),
                'message': str(exc), 'retry': '같은 확정 리비전으로 pdf 명령을 다시 실행하세요. 기획서는 변경되지 않습니다.'}
    finally:
        if pending is not None:
            shutil.rmtree(pending, ignore_errors=True)
        if locked:
            lock.rmdir()
