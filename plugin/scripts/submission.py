#!/usr/bin/env python3
"""Read bundled submissions without searching the user's filesystem."""
import argparse
import json
import re
from pathlib import Path

NAMES = ('product-compliance', 'spec-policy', 'weekly-report', 'standard-time')

def prepare(name, root=None, product=False, linked=False):
    if name not in NAMES:
        raise ValueError('unknown bundled example')
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    candidates = (root / 'examples' / (name + '.md'), root.parent / 'examples' / (name + '.md'))
    source = next((p for p in candidates if p.is_file()), None)
    if source is None:
        raise FileNotFoundError('bundled example missing')
    text = source.read_text(encoding='utf-8')
    result = {'submission': {'text': text, 'source': str(source)}, 'evidence': 'provided_example_not_verified_performance'}
    if name == 'standard-time':
        match = re.search(r'단순 공정\s*(\d+)h\s*/\s*복잡 공정\s*(\d+)h', text)
        if not match or '소요 시간' not in text or '라인 구성 시' not in text:
            raise ValueError('ST source changed: review mapping before using prefill')
        result['prefill'] = {
            'scope': '실측값 입력으로 ST 자동 산출하는 엑셀 템플릿 + 각 공정 담당자가 측정할 방법·판단 기준 가이드',
            'unit': '공정 1건',
            'trigger': '라인 구성 시',
            'source_location': '엑셀 파일',
            'baseline': {'kind': 'self_report', 'meaning': '기존 제출의 소요 시간; ST 값이나 도입 후 목표가 아님', 'simple_hours': int(match[1]), 'complex_hours': int(match[2]), 'all_people_and_review_scope': None},
            'regular_update_frequency': None,
            'independent_measurement_rate': None,
            'st_formula': None,
            'approval_rule': None,
        }
        result['question_contract'] = {
            'already_answered_do_not_ask': ['공정 1건의 정의', '현재 소요 시간', '현재인지 목표인지 재분류', '측정 계기', '자료 위치'],
            'possible_next_gaps': ['시간이 집중되는 작업 단계', '검토·승인 완료 기준'],
            'rules': ['단순/복잡 조건 보존', '미확인 비율을 추정 0%로 채우지 않음', '측정 계기와 정기 갱신 주기는 구분; 계기 재질문 금지', '전체 사람시간 포함 범위는 향후 비교 기록에서 확인하며 기존 시간 전체를 미확인으로 되돌리지 않음']
        }
    if product or linked:
        result['planning_scope'] = 'product'
        if 'prefill' in result:
            result['prefill'] = {k: v for k, v in result['prefill'].items() if k in ('scope', 'unit', 'trigger', 'source_location', 'st_formula')}
        result['question_contract'] = {
            'already_answered_do_not_ask': ['원문 업무 범위', '측정 계기', '기존 소요 시간'],
            'out_of_scope_do_not_ask': ['KPI', '회사 의도 정합성 판정', '생산력', '기준선', '전체 참여자 시간', '정기 갱신 주기', '절감 시간 사용처'],
            'possible_next_gaps': ['구현할 입력 파일의 열 구조', '결과 파일의 사용 방식', '현업 계산 규칙 원문'],
            'rules': ['원문을 먼저 읽고 이미 제공된 답은 재사용', '기술적 정상/예외 시험은 유지', '승인을 별도 관리 기능으로 확대하지 않음', '실제 자료가 없으면 구현 가능한 틀과 자료 확인 후 계산을 구분']
        }
    if linked:
        result["planning_contract"] = "objective-linkage-v1"
        q = result["question_contract"]
        q["out_of_scope_do_not_ask"].remove("KPI")
        q["possible_next_gaps"] = ["목표·활용 미확인이고 재사용이 타당할 때 원문 기반 축적·활용 가설 선제안 → 선택/수정/아직 모름 → 필요한 기록 설계", "기존 목적 KPI 재사용 또는 선택된 활용의 품질·실제 사용 KPI 하나 제안/사람 확인", "기존 업무 앱 입력·트리거·결과 레코드", "KPI에 연결할 결과·근거·기록 계기/식별자; 외부 전달처는 선택"]
        q["rules"] += ["제출 업무는 변경 후보이며 KPI를 임의 선택/확정하지 않음", "목표 미확정은 초안 유지; 나머지 설계 진행", "새 폼·대시보드·다운로드보다 기존 앱 재사용 우선", "실제 앱/API 접속 또는 측정 검증을 주장하지 않음", "확인된 목표·활용과 시간 KPI는 유지; 일회성·비축적 업무에 재사용을 강제하지 않음"]
    return result

if __name__ == '__main__':
    from portable import configure_stdio
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument('--example', required=True, choices=NAMES)
    parser.add_argument("--product", action="store_true")
    parser.add_argument("--linked", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.example, product=args.product, linked=args.linked), ensure_ascii=False, indent=2))
