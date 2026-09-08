"""Synthetic Camp edge fixtures exercised through the actual packaging helper."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qa_claude as qa


class CampEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='camp-edge-')
        cls.root = Path(cls.tmp.name) / 'run'
        names = ['camp-corrupt', 'camp-other-project', 'camp-sensitive-key',
                 'camp-oversize', 'camp-source-injection']
        with contextlib.redirect_stdout(io.StringIO()):
            prepared = qa.prepare(cls.root, 'claude-sonnet-4-6', '2.1.263', names)
        # prepare resolves Windows short-name temp paths before recording cwd.
        # Use that returned root when passing the project back to the helper.
        cls.root = Path(prepared['directory'])
        cls.cases = {c['scenario']['id']: c for c in qa.read(cls.root / 'manifest.json')['cases']}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def inputs(self, name):
        case = self.cases[name]
        work = self.root / name / 'work'
        source = work / case['scenario']['session_paths']['a']
        output = work / '.sparker-submissions' / 'edge.zip'
        return case, work, source, output

    def package(self, work, source, output):
        return qa.camp_submit.prepare(work / '.sparker-discovery', 'qa-case', 1, 1,
                                      work, [source], output, include_raw=True)

    def test_invalid_raw_inputs_reject_without_rewriting_or_archive(self):
        for name, reason in [('camp-corrupt', '번째 줄'),
                             ('camp-other-project', '프로젝트 밖'),
                             ('camp-oversize', '5 MiB')]:
            with self.subTest(name=name):
                case, work, source, output = self.inputs(name)
                before = source.read_bytes()
                if name == 'camp-oversize':
                    self.assertLess(len(before), qa.camp_submit.MAX_FILE)
                    packed = qa.camp_submit.make_zip({'sessions/' + source.name: before})
                    self.assertGreater(len(packed), qa.camp_submit.MAX_ZIP)
                with self.assertRaisesRegex(qa.plan.PlanError, reason):
                    self.package(work, source, output)
                self.assertFalse(output.exists())
                self.assertEqual(source.read_bytes(), before)
                _, records = qa.inspect_records(work, case['scenario'], {})
                qa.finish_checks(work, case['scenario'], records)

    def test_rejected_input_cannot_pass_by_silently_omitting_session(self):
        case, work, source, output = self.inputs('camp-corrupt')
        qa.camp_submit.prepare(work / '.sparker-discovery', 'qa-case', 1, 1,
                               work, [], output)
        try:
            _, records = qa.inspect_records(work, case['scenario'], {})
            with self.assertRaisesRegex(ValueError, 'invalid Camp input produced an archive'):
                qa.finish_checks(work, case['scenario'], records)
        finally:
            output.unlink()

    def test_sensitive_fixture_warns_without_disclosing_or_masking_value(self):
        case, work, source, output = self.inputs('camp-sensitive-key')
        report = self.package(work, source, output)
        secret = 'sk-ant-' + 'x' * 40
        self.assertIn(secret, source.read_text())
        self.assertTrue(any(f['kind'] == 'api-key' for f in report['possible_secrets']))
        self.assertNotIn(secret, json.dumps(report))
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.read('sessions/' + source.name), source.read_bytes())
        _, records = qa.inspect_records(work, case['scenario'], {})
        qa.finish_checks(work, case['scenario'], records)

    def test_source_injection_remains_literal_selected_session_data(self):
        case, work, source, output = self.inputs('camp-source-injection')
        canary = work.parent / 'CANARY.txt'
        before = canary.read_bytes()
        self.package(work, source, output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.read('sessions/' + source.name), source.read_bytes())
            self.assertNotIn('CANARY.txt', archive.namelist())
            self.assertEqual(len([n for n in archive.namelist() if n.startswith('sessions/')]), 1)
        self.assertEqual(canary.read_bytes(), before)
        _, records = qa.inspect_records(work, case['scenario'], {})
        qa.finish_checks(work, case['scenario'], records)


if __name__ == '__main__':
    unittest.main()
