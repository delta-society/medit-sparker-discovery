"""All KPI confirmations, apps and mappings here are synthetic, not live evidence."""
import copy
import json
from pathlib import Path
import shutil
import sys
import unittest

import test_product
from test_product import product
from test_plan import p, confirmation, SCRIPT
sys.path.insert(0, str(SCRIPT.parent))
import linkage


def linked(confirmed=True, bound=False):
    plan = product()
    plan.update(linkage.template())
    o = plan['objective']
    o.update(outcome='합성: 납기 준수', metric_reference='synthetic-proposal:on-time',
             definition='약속일 이내 품질 통과 납품 건수 / 납품 대상 건수',
             quality='검토 통과 납품만 인정; 취소 분리', unit='%',
             source='합성: 기존 납품 기록의 약속일·완료일·검토 상태', desired_direction='높일 것',
             causal_relation='누락 검사 → 정정 지연 감소 → 납기 준수 증가 가설',
             alignment_owner='외부 과제 프로그램(합성)', measurement_owner='외부 측정 프로그램(합성)',
             status='proposed')
    if confirmed:
        o['status'] = 'human_confirmed'
        o['confirmation'] = dict(actor='human', quote='합성 확인 — 실제 사람이 선택한 KPI 아님',
                                 explicit=True, definition_sha256=linkage.objective_digest(o))
    plan['linkage'].update(surface_strategy='reuse_existing', reuse_basis='합성: 기존 업무 앱 레코드를 입력/결과로 재사용')
    plan['acquisition_tasks'].append(dict(id='get-link', what='미확인 앱/ID/필드/이벤트/중복/실패 계약 확보',
        owner='업무 앱 담당 후보(미확정)', method='비식별 계약 사본과 권한 범위를 담당에게 요청',
        done_when='원천 레코드→결과 상태→측정 이벤트 매핑 근거 확보'))
    for name, keys in linkage.LINKS.items():
        x = plan['linkage'][name]
        x['acquisition_ids'] = ['get-link']
        x['status'] = 'unknown'
        if bound:
            x.update({key: 'synthetic mapping: record-1 → field/state/event-1' for key in keys})
            x.update(status='bound', basis='합성 계약 사본 (실제 앱 조회 아님)', acquisition_ids=[])
    if bound:
        plan['linkage']['measurement']['metric_reference'] = o['metric_reference']
    return plan


def linked_confirmation(record):
    c = confirmation(record)
    c['scopes'] += linkage.SCOPES
    return c


class LinkageTests(unittest.TestCase):
    setUp = test_product.ProductTests.setUp
    tearDown = test_product.ProductTests.tearDown
    cli = test_product.ProductTests.cli
    input_file = test_product.ProductTests.input_file

    def test_partial_template_and_unknown_kpi_never_finalize(self):
        plan = self.cli('template', '--linked')
        self.assertEqual(plan, p.template(linked=True))
        self.assertIs(p.validate_plan(plan), plan)
        first = self.store.write('partial', 'new', plan=plan)
        self.assertEqual(self.store.load('partial'), first)
        self.assertIn('목적 KPI', p.markdown(first))
        for candidate in [plan, linked(confirmed=False)]:
            p.validate_plan(candidate)
            with self.assertRaises(p.PlanError):
                p.validate_plan(candidate, complete=True)
        full = self.store.write('no-kpi-choice', 'new', plan=linked(confirmed=False))
        with self.assertRaisesRegex(p.PlanError, '목표 KPI 미확정'):
            self.store.write('no-kpi-choice', 'finalize', expected=1, confirmation=linked_confirmation(full))
        self.assertEqual(self.store.load('no-kpi-choice')['status'], 'draft')

    def test_confirmed_outcome_unknown_apps_complete_with_acquisition(self):
        plan = linked()
        self.assertNotIn('baseline', plan)
        self.assertNotIn('labor_hours', json.dumps(plan))
        p.validate_plan(plan, complete=True)
        inp = self.input_file('linked.json', plan)
        self.cli('validate', '--input', inp, '--complete')
        self.cli('new', 'linked-case', '--input', inp)
        first = self.cli('show', 'linked-case')
        with self.assertRaises(p.PlanError):
            p.validate_confirmation(confirmation(first), first)
        c = self.input_file('confirm.json', linked_confirmation(first))
        self.cli('finalize', 'linked-case', '--expected-revision', '1', '--confirmation', c)
        final = self.cli('resume', 'linked-case')
        self.assertEqual(final['status'], 'finalized')
        target = self.base / 'linked.md'
        self.cli('export', 'linked-case', '--output', str(target))
        md = target.read_text()
        for value in ['납기 준수', '원하는 변화 방향', '인과 가설', 'get-link', '권한 범위', 'unknown', '운영 준비 검증이 아닙니다']:
            self.assertIn(value, md)
        self.cli('reopen', 'linked-case', '--expected-revision', '2', '--reason', '합성 수정 요청')
        plan['open_questions'].append('실제 매핑 자료 확보 전 실행 금지')
        inp = self.input_file('update.json', plan)
        self.cli('update', 'linked-case', '--expected-revision', '3', '--reason', '미결 명시', '--input', inp)
        self.assertEqual(self.cli('show', 'linked-case')['revision'], 4)

    def test_bound_is_contract_not_live_and_missing_details_rejected(self):
        plan = linked(bound=True)
        p.validate_plan(plan, complete=True)
        for name, keys in linkage.LINKS.items():
            for key in [*keys, 'basis']:
                bad = copy.deepcopy(plan)
                bad['linkage'][name][key] = ''
                with self.subTest(name=name, key=key), self.assertRaises(p.PlanError):
                    p.validate_plan(bad)
        for state in ['unknown', 'draft']:
            plan = linked()
            for name in linkage.LINKS:
                plan['linkage'][name]['status'] = state
            p.validate_plan(plan, complete=True)
            for name in linkage.LINKS:
                bad = copy.deepcopy(plan)
                bad['linkage'][name]['acquisition_ids'] = []
                p.validate_plan(bad)  # Early draft allowed.
                with self.assertRaises(p.PlanError):
                    p.validate_plan(bad, complete=True)
        for state in ['live', 'verified', [], None]:
            bad = linked()
            bad['linkage']['upstream']['status'] = state
            with self.assertRaises(p.PlanError):
                p.validate_plan(bad)

    def test_objective_definition_confirmation_stale_and_fabricated_fields(self):
        for key in linkage.OBJECTIVE:
            bad = linked()
            bad['objective'][key] += ' changed'
            with self.subTest(key=key), self.assertRaisesRegex(p.PlanError, '다시 확인'):
                p.validate_plan(bad)
        edits = [lambda x: x['objective'].update(confirmation=None),
                 lambda x: x['objective']['confirmation'].update(actor='ai'),
                 lambda x: x['objective']['confirmation'].update(quote=''),
                 lambda x: x['objective'].update(numeric_target=50),
                 lambda x: x['linkage']['measurement'].update(metric_reference='wrong'),
                 lambda x: x['linkage']['upstream'].update(acquisition_ids=['missing']),
                 lambda x: x.update(planning_contract='invented'),
                 lambda x: x.pop('objective'),
                 lambda x: x.pop('linkage')]
        for edit in edits:
            bad = linked()
            edit(bad)
            with self.subTest(edit=edit), self.assertRaises(p.PlanError):
                p.validate_plan(bad)

    def test_no_downgrade_and_no_mutation(self):
        plan = linked()
        before = copy.deepcopy(plan)
        p.validate_plan(plan, complete=True)
        self.assertEqual(plan, before)
        self.store.write('no-downgrade', 'new', plan=plan)
        for key in ['planning_contract', 'objective', 'linkage']:
            plan.pop(key)
        with self.assertRaisesRegex(p.PlanError, '하향'):
            self.store.write('no-downgrade', 'update', plan=plan, expected=1, reason='bypass attempt')

    def test_real_030_fixture_load_upgrade_preserves_bytes(self):
        source = Path(__file__).parent / 'fixtures' / 'legacy-product' / 'case-product'
        target = self.store.case_path('case-product')
        shutil.copytree(source, target)
        snapshots = {x: x.read_bytes() for x in target.rglob('*') if x.is_file()}
        old = self.store.load('case-product')
        self.assertEqual(old['status'], 'finalized')
        self.store.write('case-product', 'reopen', expected=2, reason='합성 목표·연동 보정')
        self.store.write('case-product', 'update', expected=3, reason='합성 0.4 계약 추가', plan=linked())
        self.assertEqual(self.store.load('case-product')['plan']['planning_contract'], linkage.CONTRACT)
        for path, raw in snapshots.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_record_only_no_destination_finalizes_and_preserves_records(self):
        plan = linked()
        plan['objective']['measurement_owner'] = ''
        plan['objective']['confirmation']['definition_sha256'] = linkage.objective_digest(plan['objective'])
        m = plan['linkage']['measurement']
        m.update(status='record_only', app='', acquisition_ids=[],
                 metric_reference=plan['objective']['metric_reference'],
                 event_mapping='합성: 업무 검토 완료 때 실제 결과와 근거를 기록',
                 record_mapping='합성: case ID + 실행 ID + KPI 참조 + 출처 + 관측/추정 구분',
                 dedupe='동일 실행 ID는 중복 집계하지 않고 변경 이력 보존',
                 failure='미확인 값은 미확인 유지; 실패/수정 이력 보존',
                 basis='합성 기획: 전달처 선택 없이 기록 설계만')
        p.validate_plan(plan, complete=True)
        first = self.store.write('record-only', 'new', plan=plan)
        self.store.write('record-only', 'finalize', expected=1, confirmation=linked_confirmation(first))
        final = self.store.load('record-only')
        self.assertEqual(final['status'], 'finalized')
        self.assertEqual(final['plan']['linkage']['measurement']['app'], '')
        self.assertIn('미지정 — 기록만 유지', p.markdown(final))
        for key in [k for k in linkage.LINKS['measurement'] if k != 'app'] + ['basis']:
            bad = copy.deepcopy(plan)
            bad['linkage']['measurement'][key] = ''
            p.validate_plan(bad)
            with self.subTest(key=key), self.assertRaises(p.PlanError):
                p.validate_plan(bad, complete=True)
        bad = copy.deepcopy(plan)
        bad['linkage']['upstream']['status'] = 'record_only'
        with self.assertRaises(p.PlanError):
            p.validate_plan(bad)

    def test_new_values_are_escaped(self):
        plan = linked(confirmed=False)
        plan['objective']['outcome'] = '<script>[bad]`</script>'
        plan['linkage']['upstream']['fields'] = '<img src=x>'
        r = self.store.write('escaped', 'new', plan=plan)
        md = p.markdown(r)
        self.assertNotIn('<script>', md)
        self.assertNotIn('<img', md)
        self.assertIn('&lt;script&gt;', md)


if __name__ == '__main__':
    unittest.main()
