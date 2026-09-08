"""PDF-only presentation: field provenance, fallback and long-content regression."""
import copy
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'scripts')]
from test_plan import complete, confirmation
from test_linkage import linked, linked_confirmation
from plan import Store, markdown
from pdf_export import assets, make_html
from pdf_presentation import hints, display
from pdf_browser import print_pdf

BROWSER = os.environ.get('SPARKER_PDF_TEST_BROWSER')
NORMAL = lambda text: ' '.join(text.split())
SNAPSHOT = '''<script>
window.__sparkerPdfReady = window.__sparkerPdfReady.then(result => ({...result, testSnapshot: {
  text: document.getElementById('document-body').textContent,
  compounds: [...document.querySelectorAll('.compound-values')].map(block => [...block.querySelectorAll('.detail-row')].map(row => [...row.children].map(cell => cell.textContent))),
  metrics: [...document.querySelectorAll('.measurement-table tbody tr')].map(row => [...row.children].map(cell => cell.textContent)),
  tests: [...document.querySelectorAll('.test-comparison tbody tr')].map(row => [...row.children].map(cell => cell.textContent)),
  longBlocks: document.querySelectorAll('.long-block').length,
  flowCaptions: [...document.querySelectorAll('.workflow-diagram figcaption')].map(node => node.textContent)
}}));
</script>'''


class DesignHintsTests(unittest.TestCase):
    def test_product_hints_do_not_include_legacy_or_unreferenced_fields(self):
        plan = linked()
        plan['baseline'] = complete()['baseline']
        plan['baseline']['people_time']['source'] = 'PRIVATE_LEGACY_SENTINEL'
        result = hints(plan)
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result['metrics'], [])
        self.assertNotIn('PRIVATE_LEGACY_SENTINEL', encoded)
        self.assertNotIn(plan['acquisition_tasks'][-1]['what'], encoded)
        self.assertIn(plan['acquisition_tasks'][0]['what'], encoded)

    def test_hints_keep_delimiters_and_display_newline_semantics(self):
        plan = complete()
        value = '첫 줄 / 담당: 실제 값\n두 줄 & <원문> # 숫자'
        plan['acquisition_tasks'][0]['method'] = value
        result = hints(plan)
        self.assertEqual(result['compounds'][0]['fields'][2], ['방법', display(value)])
        self.assertIn(display(value), result['compounds'][0]['expected'])
        self.assertEqual(result['compounds'][1]['heading'], '6. 구현 순서')


@unittest.skipUnless(BROWSER and shutil.which('pdftotext'), 'opt-in browser + developer pdftotext')
class RenderDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle, _ = assets()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pdf-design-')
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, plan, mutate=None):
        store = Store(self.root / '확정 기획')
        draft = store.write('test', 'new', plan=plan)
        confirm = linked_confirmation(draft) if 'planning_contract' in plan else confirmation(draft)
        record = store.write('test', 'finalize', expected=1, confirmation=confirm)
        immutable = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in store.root.rglob('plan.*')}
        document = make_html(record, self.bundle)
        start = document.index('type="application/json">') + len('type="application/json">')
        end = document.index('</script>', start)
        payload = json.loads(document[start:end])
        self.assertEqual(payload['markdown'], markdown(record))
        if mutate:
            mutate(payload)
            document = document[:start] + json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c') + document[end:]
        self.assertTrue(document.endswith('</body></html>'))
        document = document[:-len('</body></html>')] + SNAPSHOT + '</body></html>'
        raw, observation = print_pdf(document, '<span></span>', browser=BROWSER)
        path = self.root / 'review.pdf'
        path.write_bytes(raw)
        extracted = subprocess.check_output(['pdftotext', str(path), '-'], text=True)
        self.assertEqual(immutable, {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in store.root.rglob('plan.*')})
        return observation, extracted

    def test_delimiter_values_keep_their_field_mapping(self):
        plan = complete()
        method = 'VALUE_START / 담당: 값 안의 문자열\n방법: 두 줄 & <원문> # VALUE_END'
        plan['acquisition_tasks'][0]['method'] = method
        plan['baseline']['people_time']['per'] = '업무 / 비교 단위'
        plan['baseline']['people_time']['source'] = '근거 / 위치\n둘째 줄'
        observation, text = self.render(plan)
        self.assertEqual(observation['presentation']['unmatchedHints'], 0)
        self.assertEqual(observation['presentation']['compounds'], 2)
        snapshot = observation['testSnapshot']
        self.assertIn(['방법', display(method)], snapshot['compounds'][0])
        self.assertEqual(snapshot['metrics'][0][2], '업무 / 비교 단위')
        self.assertEqual(snapshot['metrics'][0][4], '근거 / 위치 / 둘째 줄')
        for index, key in enumerate(['input', 'steps', 'expected', 'pass_condition', 'runner']):
            for column, case in enumerate(plan['acceptance_tests'], 1):
                value = ' → '.join(case[key]) if key == 'steps' else case[key]
                self.assertEqual(NORMAL(snapshot['tests'][index][column]), NORMAL(value))
        self.assertIn('VALUE_END', text)

    def test_mismatched_hint_leaves_canonical_content(self):
        plan = complete()
        def mutate(payload):
            payload['presentation']['compounds'][0]['expected'] = 'not the canonical source'
            payload['presentation']['compounds'][0]['fields'][0][1] = 'REPLACEMENT_MUST_NOT_APPEAR'
        observation, text = self.render(plan, mutate)
        self.assertEqual(observation['presentation']['unmatchedHints'], 1)
        self.assertNotIn('REPLACEMENT_MUST_NOT_APPEAR', text)
        self.assertIn(plan['acquisition_tasks'][0]['method'], NORMAL(text))

    def test_linked_kpi_and_link_only_acquisition_preserved(self):
        plan = linked()
        plan['baseline'] = complete()['baseline']
        plan['baseline']['people_time']['source'] = 'PRIVATE_LEGACY_SENTINEL'
        observation, text = self.render(plan)
        self.assertEqual(observation['presentation']['metricRows'], 0)
        self.assertEqual(observation['presentation']['unmatchedHints'], 0)
        self.assertNotIn('PRIVATE_LEGACY_SENTINEL', text)
        compact = ''.join(text.split())
        for value in [plan['objective']['definition'], plan['objective']['causal_relation'],
                      plan['acquisition_tasks'][0]['what'], plan['acquisition_tasks'][-1]['what'],
                      plan['acquisition_tasks'][-1]['done_when']]:
            self.assertIn(''.join(value.split()), compact)

    def test_page_length_fields_and_long_flow_keep_ends(self):
        plan = complete()
        values = {
            'ACQ': 'ACQ_BEGIN ' + ' '.join(f'확보검토{i:03d}' for i in range(220)) + ' ACQ_END',
            'METRIC': 'METRIC_BEGIN ' + ' '.join(f'측정근거{i:03d}' for i in range(180)) + ' METRIC_END',
            'NEXT': 'NEXT_BEGIN ' + ' '.join(f'완료조건{i:03d}' for i in range(180)) + ' NEXT_END',
        }
        plan['acquisition_tasks'][0]['method'] = values['ACQ']
        plan['baseline']['people_time']['source'] = values['METRIC']
        plan['next_action']['done_when'] = values['NEXT']
        plan['workflow'] = [dict(plan['workflow'][0], step=f'검토 단계 {index + 1}') for index in range(18)]
        observation, text = self.render(plan)
        self.assertEqual(observation['workflowSteps'], 18)
        self.assertGreater(observation['workflowContinuations'], 0)
        self.assertGreater(observation['testSnapshot']['longBlocks'], 0)
        compact = ''.join(text.split())
        for key, value in values.items():
            self.assertIn(key + '_BEGIN', compact)
            self.assertIn(key + '_END', compact)
            self.assertIn(value, observation['testSnapshot']['text'])
        for prefix, count, copies in [('확보검토', 220, 1), ('측정근거', 180, 1), ('완료조건', 180, 2)]:
            found = [int(number) for number in re.findall(prefix + r'(\d{3})', compact)]
            self.assertEqual(found, list(range(count)) * copies)
        self.assertEqual(observation['presentation']['stackedMetrics'], 1)
        self.assertIn('18단계', ''.join(observation['testSnapshot']['flowCaptions']))

if __name__ == '__main__':
    unittest.main()
