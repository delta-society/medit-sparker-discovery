import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import submission

class SubmissionTest(unittest.TestCase):
    def test_st_prefill(self):
        r = submission.prepare('standard-time')
        self.assertIn('라인 구성 시', r['submission']['text'])
        self.assertEqual(r['prefill']['baseline']['simple_hours'], 4)
        self.assertEqual(r['prefill']['baseline']['complex_hours'], 8)
        self.assertEqual(r['prefill']['baseline']['kind'], 'self_report')
        self.assertIsNone(r['prefill']['independent_measurement_rate'])
        self.assertIsNone(r['prefill']['regular_update_frequency'])
        self.assertIn('현재 소요 시간', r['question_contract']['already_answered_do_not_ask'])

    def test_product_prefill_keeps_source_without_measurement_questions(self):
        legacy = submission.prepare('standard-time')
        r = submission.prepare('standard-time', product=True)
        self.assertEqual(r['submission'], legacy['submission'])
        self.assertEqual(r['planning_scope'], 'product')
        self.assertNotIn('baseline', r['prefill'])
        self.assertNotIn('independent_measurement_rate', r['prefill'])
        self.assertIn('가이드', r['prefill']['scope'])
        self.assertIn('KPI', r['question_contract']['out_of_scope_do_not_ask'])
        self.assertIn('현업 계산 규칙 원문', r['question_contract']['possible_next_gaps'])

    def test_product_other_example_no_st_default(self):
        r = submission.prepare('weekly-report', product=True)
        self.assertNotIn('prefill', r)
        self.assertNotIn('ST', str(r['question_contract']))

    def test_zip_layout(self):
        text = submission.prepare('standard-time')['submission']['text']
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'plugin'; (root / 'examples').mkdir(parents=True)
            (root / 'examples/standard-time.md').write_text(text, encoding='utf-8')
            self.assertEqual(submission.prepare('standard-time', root)['submission']['text'], text)

    def test_other_example_not_st(self):
        self.assertNotIn('prefill', submission.prepare('weekly-report'))

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            submission.prepare('../secrets')

    def test_changed_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'plugin'; (root / 'examples').mkdir(parents=True)
            (root / 'examples/standard-time.md').write_text('changed')
            with self.assertRaises(ValueError):
                submission.prepare('standard-time', root)
