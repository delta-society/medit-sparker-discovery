#!/usr/bin/env python3
"""Developer-only real-browser review samples; synthetic, no participant data."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'plugin/scripts'), str(REPO / 'plugin/tests')]
from test_plan import complete, confirmation
from test_linkage import linked, linked_confirmation
from plan import Store
import pdf_export


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--extended', action='store_true', help='linked, long fields and long test cases')
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Verify the release artifact, including offline JS/font assets.
    subprocess.run([sys.executable, str(REPO / 'scripts/build-package.py'), '--output', str(out / 'plugin.zip')], check=True)
    with zipfile.ZipFile(out / 'plugin.zip') as archive:
        archive.extractall(out / 'plugin')
    results = []
    for case, result, steps in [
        ('weekly-report', '합성 예시: 주간 보고 초안을 근거와 함께 검토한다', ['원천 자료 수집', '누락·중복 확인', '보고 초안 작성', '사람 검토']),
        ('ar-match', '합성 예시: 미수 대사 결과와 미확인 예외를 검토한다', ['은행·원장 자료 확보', '식별자 대조', '불일치 분리', '담당자 확인']),
        ('quality-search', '합성 예시: 불량 유사 사례 검색 결과를 출처와 함께 검토한다', ['불량 현상 입력', '근거 문서 검색', '유사 사례 검토', '적용 여부 확인']),
    ]:
        plan = complete()
        plan['user_result']['result'] = result
        plan['selected_change']['change'] = result
        plan['workflow'] = [dict(plan['workflow'][0], step=step) for step in steps]
        store = Store(out / 'ledger')
        draft = store.write(case, 'new', plan=plan)
        record = store.write(case, 'finalize', expected=1, confirmation=confirmation(draft))
        command = [sys.executable, str(out / 'plugin/scripts/plan.py'), '--root', str(store.root), 'pdf', case, '--expected-revision', '2']
        run = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=True)
        exported = json.loads(run.stdout)
        assert exported['status'] == 'ready', exported
        path = Path(exported['path'])
        (out / f'{case}.pdf').write_bytes(path.read_bytes())
        extracted = subprocess.check_output(['pdftotext', str(path), '-'], text=True)
        assert '&#' not in extracted, 'Diagram entity encoding leaked'
        assert '1. ' + steps[0] in extracted, 'Diagram label missing'
        results.append(exported)
    # Stress specimen: actual GFM tables, Korean, long links, fenced Mermaid.
    bundle, _ = pdf_export.assets()
    document = pdf_export.make_html(record, bundle)
    start = document.index('type="application/json">') + len('type="application/json">')
    end = document.index('</script>', start)
    payload = json.loads(document[start:end])
    payload['markdown'] += '\n## 긴 표 합성 검증\n\n| 번호 | 검토 내용 | 근거 |\n| --- | --- | --- |\n'
    payload['markdown'] += ''.join(f'| {i} | 한글 표의 페이지 분할과 내용 보존 검증 {i} | 합성 자료 {i} |\n' for i in range(1, 101))
    payload['markdown'] += '\n```mermaid\nflowchart TD\n A[자료 확인] --> B[사람 검토]\n```\n\n마지막행확인 100\n'
    payload['markdown'] += '\n<script>window.pwned=true</script>\n![외부 이미지](https://invalid.example/tracker)\n'
    document = document[:start] + json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c') + document[end:]
    raw, observation = pdf_export.print_pdf(document, '<span></span>')
    (out / 'long-table.pdf').write_bytes(raw)
    results.append(observation)
    if args.extended:
        long_fields = complete()
        long_fields['acquisition_tasks'][0]['method'] = '긴확보시작 ' + ' '.join(f'확보검토{i:03d}' for i in range(220)) + ' 긴확보끝'
        long_fields['baseline']['people_time']['source'] = '긴근거시작 ' + ' '.join(f'측정근거{i:03d}' for i in range(180)) + ' 긴근거끝'
        long_fields['next_action']['done_when'] = '긴완료시작 ' + ' '.join(f'완료조건{i:03d}' for i in range(180)) + ' 긴완료끝'
        long_fields['workflow'] = [dict(long_fields['workflow'][0], step=f'검토 단계 {index + 1}') for index in range(18)]
        long_tests = complete()
        long_tests['acceptance_tests'][0]['input'] = '긴시험시작 ' + ' '.join(f'정상입력{i:03d}' for i in range(130)) + ' 긴시험끝'
        long_tests['quality_conditions'].append('긴식별자 ' + 'IDENTIFIER_' * 85 + ' IDENTIFIER_END')
        for case, plan, confirm in [('linked-plan', linked(), linked_confirmation),
                                     ('long-fields', long_fields, confirmation),
                                     ('long-tests', long_tests, confirmation)]:
            store = Store(out / 'ledger')
            draft = store.write(case, 'new', plan=plan)
            store.write(case, 'finalize', expected=1, confirmation=confirm(draft))
            command = [sys.executable, str(out / 'plugin/scripts/plan.py'), '--root', str(store.root), 'pdf', case, '--expected-revision', '2']
            result = json.loads(subprocess.check_output(command, text=True, encoding='utf-8'))
            assert result['status'] == 'ready', result
            (out / f'{case}.pdf').write_bytes(Path(result['path']).read_bytes())
            results.append(result)
    # Text/size checks are developer-only; the release needs neither Poppler nor Pillow.
    for path in sorted(out.glob('*.pdf')):
        info = subprocess.check_output(['pdfinfo', str(path)], text=True)
        assert '(A4)' in info, path
        content = subprocess.check_output(['pdftotext', str(path), '-'], text=True)
        compact = ''.join(content.split())
        assert content.strip(), path
        if path.stem == 'long-table':
            assert '마지막행확인100' in compact
        if path.stem == 'long-fields':
            for marker in ['긴확보끝', '긴근거끝', '긴완료끝', '18단계']:
                assert marker in compact, (path, marker)
        if path.stem == 'long-tests':
            assert '긴시험끝' in compact and 'IDENTIFIER_END' in compact
        if path.stem == 'linked-plan':
            assert '목적KPI' in compact and '외부' in compact
    (out / 'verification.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'samples': str(out), 'outputs': len(results)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
