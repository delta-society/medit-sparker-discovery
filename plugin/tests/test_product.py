"""Product-only contracts; all records and confirmations are synthetic fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_plan import SCRIPT, complete, confirmation, p

sys.path.insert(0, str(SCRIPT.parent))
import kpi


def product():
    plan = complete()
    for key in ['submission', 'facts', 'bottlenecks', 'baseline', 'comparison']:
        del plan[key]
    plan['planning_scope'] = 'product'
    plan['selected_change'].update(candidate_id=None, reason='')
    plan['workflow'][0].update(basis='', wait_or_rework='')
    plan['open_questions'] = ['CSV 인코딩은 UTF-8인가?']
    return plan


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.store = p.Store(self.base / 'cases')

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.store.root), *args],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stdout + result.stderr)
        return json.loads(result.stdout if ok else result.stderr)

    def input_file(self, name, value):
        path = self.base / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return str(path)

    def test_template_and_full_cli_product_lifecycle(self):
        self.assertEqual(self.cli('template'), p.template())
        template = self.cli('template', '--product')
        self.assertEqual(template, p.template(product=True))
        p.validate_plan(template)
        for field in ['kpi', 'baseline', 'comparison', 'bottlenecks', 'facts', 'submission']:
            self.assertNotIn(field, template)
        plan = product()
        before = copy.deepcopy(plan)
        self.assertIs(p.validate_plan(plan, complete=True), plan)
        self.assertEqual(plan, before)
        inp = self.input_file('input.json', plan)
        first = self.cli('new', 'product-case', '--input', inp)
        immutable = Path(first['directory']) / 'plan.json'
        original_bytes = immutable.read_bytes()
        plan['next_action']['action'] = 'CSV 검사 함수부터 구현'
        inp = self.input_file('input.json', plan)
        self.cli('update', 'product-case', '--input', inp, '--expected-revision', '1', '--reason', '구현 순서 구체화')
        current = self.cli('show', 'product-case')
        self.assertEqual(current['plan'], plan)
        conf = self.input_file('confirmation.json', confirmation(current))
        result = self.cli('finalize', 'product-case', '--expected-revision', '2', '--confirmation', conf)
        self.assertEqual(result['status'], 'finalized')
        final = self.cli('show', 'product-case')
        self.assertEqual(final['plan'], plan)
        self.assertIsNone(final['plan']['selected_change']['candidate_id'])
        target = self.base / 'product.md'
        self.cli('export', 'product-case', '--output', str(target))
        self.assertEqual(target.read_text(encoding='utf-8'), p.markdown(final))
        self.assertEqual(immutable.read_bytes(), original_bytes)

    def test_legacy_markdown_golden_hashes_and_load_unchanged(self):
        # Captured from the pre-product renderer, not regenerated from new code.
        hashes = {'draft': '1ff3ee31a045a58fc44eec10017b732c61f2c1f25865ea892cc742c1a02ccb96',
                  'finalized': 'c85e8212b8fd0e669e1ba801a3f2c460c262c81802a94cf158f81d54db31c781'}
        first = self.store.write('legacy-case', 'new', plan=complete())
        conf = confirmation(first)
        conf['quote'] = 'legacy confirmation'
        final = self.store.write('legacy-case', 'finalize', expected=1, confirmation=conf)
        snapshots = {}
        for record in [first, final]:
            md = p.markdown(record)
            self.assertEqual(hashlib.sha256(md.encode()).hexdigest(), hashes[record['status']])
            self.assertNotIn('planning_scope', record['plan'])
            directory = self.store.case_path('legacy-case') / f"r{record['revision']:06d}"
            for name in ['plan.json', 'plan.md']:
                path = directory / name
                snapshots[path] = path.read_bytes()
        self.assertEqual(self.store.load('legacy-case'), final)
        for path, raw in snapshots.items():
            self.assertEqual(path.read_bytes(), raw)
        md_path = self.store.case_path('legacy-case') / 'r000002' / 'plan.md'
        md_path.write_text(p.markdown(final) + '\n', encoding='utf-8')
        with self.assertRaisesRegex(p.PlanError, 'Markdown/JSON'):
            self.store.load('legacy-case')

    def test_optional_private_data_not_rendered_or_required_complete(self):
        plan = product()
        legacy = complete()
        for key in ['submission', 'facts', 'bottlenecks', 'baseline', 'comparison']:
            plan[key] = legacy[key]
        plan['submission'] = dict(text='PRIVATEsubmission', source='/private/PRIVATEsource')
        plan['facts'][0].update(text='PRIVATEfact', source='/private/PRIVATEfactpath')
        plan['bottlenecks'][0].update(claim='PRIVATEclaim', counterevidence=[])
        plan['selected_change']['reason'] = 'PRIVATEcausal'
        plan['workflow'][0].update(basis='PRIVATEbasis', wait_or_rework='PRIVATEwait')
        for metric in plan['baseline'].values():
            metric.update(source='PRIVATEbaseline', per='PRIVATEunit')
        plan['comparison'] = {key: 'PRIVATEcomparison' for key in legacy['comparison']}
        plan['kpi'] = kpi.template()
        plan['kpi']['rationale'] = 'PRIVATEkpi'
        plan['kpi']['measurement_plan']['source'] = '/private/PRIVATEmeasurement'
        plan['acquisition_tasks'].append(dict(id='unused', what='PRIVATEacquisition', owner='owner', method='method', done_when='done'))
        p.validate_plan(plan, complete=True)
        first = self.store.write('private-case', 'new', plan=plan)
        conf = confirmation(first)
        conf['quote'] = 'PRIVATEconfirmation'
        final = self.store.write('private-case', 'finalize', expected=1, confirmation=conf)
        md = p.markdown(final)
        for sentinel in ['PRIVATE', '/private/', 'KPI', '최초 제출', '근거와 구분', '전후 측정', '효과 확인', '확정 발화']:
            self.assertNotIn(sentinel, md)
        for expected in ['정상 입력 시험', '예외 입력 시험', '예상 결과', '누락 열 이름 오류', '행 누락/중복', '비식별 시험 CSV', 'UTF-8']:
            self.assertIn(expected, md)
        self.assertEqual(self.store.load('private-case')['plan'], plan)
        plan['comparison'] = {key: '' for key in legacy['comparison']}
        plan['bottlenecks'][0].update(evidence=[], counterevidence=[])
        p.validate_plan(plan, complete=True)

    def test_product_normal_exception_and_build_requirements_remain(self):
        edits = [lambda x: x['acceptance_tests'].pop(0),
                 lambda x: x['acceptance_tests'].pop(),
                 lambda x: x['acceptance_tests'][0].update(steps=[]),
                 lambda x: x['acceptance_tests'][1].update(expected=''),
                 lambda x: x['selected_change'].update(change=''),
                 lambda x: x['selected_change'].update(non_goals=[]),
                 lambda x: x['responsibilities'].update(code=[]),
                 lambda x: x.update(acquisition_tasks=[]),
                 lambda x: x['next_action'].update(action='')]
        for key in ['user', 'result', 'use_when']:
            edits.append(lambda x, key=key: x['user_result'].update({key: ''}))
        for key in ['inputs', 'quality_conditions', 'implementation_steps']:
            edits.append(lambda x, key=key: x.update({key: []}))
        for edit in edits:
            plan = product()
            edit(plan)
            with self.subTest(edit=edit), self.assertRaises(p.PlanError):
                p.validate_plan(plan, complete=True)

    def test_optional_legacy_types_still_checked(self):
        for key, value in [('kpi', []), ('baseline', []), ('comparison', []), ('facts', {}), ('submission', None), ('bottlenecks', {})]:
            plan = product()
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.validate_plan(plan, complete=True)
        plan = product()
        plan['kpi'] = kpi.template()
        plan['kpi']['before']['labor_hours'] = 'not a number'
        with self.assertRaises(ValueError):
            p.validate_plan(plan, complete=True)
        plan = product()
        plan['baseline'] = p.template()['baseline']
        plan['baseline']['people_time']['value'] = 0
        with self.assertRaises(p.PlanError):
            p.validate_plan(plan, complete=True)

    def test_unknown_or_malicious_marker_cannot_bypass_validation(self):
        for marker in ['legacy', 'PRODUCT', '', '../product', 'product; touch sentinel', None, True, [], {}]:
            for factory in [complete, product]:
                plan = factory()
                plan['planning_scope'] = marker
                with self.subTest(marker=marker, factory=factory.__name__), self.assertRaises(p.PlanError):
                    p.validate_plan(plan)
        plan = product()
        plan['unrecognized'] = True
        with self.assertRaises(p.PlanError):
            p.validate_plan(plan)

    def test_product_labels_and_values_are_inert(self):
        plan = product()
        plan['workflow'][0]['step'] = '<script>bad</script>'
        plan['inputs'][0]['name'] = '[link](https://invalid.example)'
        plan['user_result']['result'] = '```<script>bad</script>'
        first = self.store.write('inert-case', 'new', plan=plan)
        md = p.markdown(first)
        self.assertNotIn('<script>', md)
        self.assertNotIn('[link]', md)
        self.assertNotIn('```', md)
        self.assertIn('&lt;script&gt;', md)
        self.assertEqual(self.store.load('inert-case')['plan'], plan)
        with self.assertRaises(p.PlanError):
            self.store.write('inert-case', 'finalize', expected=1)

    def test_existing_legacy_draft_can_switch_without_rewriting_history(self):
        first = self.store.write('switch-case', 'new', plan=complete())
        directory = self.store.case_path('switch-case') / 'r000001'
        before = {name: (directory / name).read_bytes() for name in ['plan.json', 'plan.md']}
        changed = copy.deepcopy(first['plan'])
        changed['planning_scope'] = 'product'
        changed['comparison'] = {key: '' for key in changed['comparison']}
        changed['bottlenecks'] = []
        changed['selected_change'].update(candidate_id=None, reason='')
        updated = self.store.write('switch-case', 'update', plan=changed, expected=1, reason='제품 전용')
        self.store.write('switch-case', 'finalize', expected=2, confirmation=confirmation(updated))
        self.assertEqual(self.store.load('switch-case')['plan'], changed)
        for name, raw in before.items():
            self.assertEqual((directory / name).read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
