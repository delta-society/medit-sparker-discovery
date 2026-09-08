"""Runner selection and Actions output tests; never dispatch CI or models."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qa'))
import ci_matrix


class MatrixTests(unittest.TestCase):
    def test_default_keeps_all_eight_native_jobs(self):
        matrix = ci_matrix.build_matrix({'run_id': 'synthetic'})
        self.assertEqual(matrix['os'], ['windows-2022', 'macos-15'])
        self.assertEqual(matrix['group'], ['planning', 'finalize', 'camp', 'reuse'])
        self.assertEqual(len(matrix['os']) * len(matrix['group']), 8)

    def test_targeted_retry_selects_only_one_native_job(self):
        self.assertEqual(ci_matrix.build_matrix({'runner_oses': ['macos-15'], 'groups': ['finalize']}),
                         {'os': ['macos-15'], 'group': ['finalize']})
        self.assertEqual(ci_matrix.build_matrix({'groups': ['reuse', 'camp']})['os'],
                         list(ci_matrix.RUNNER_OSES))

    def test_rejects_untrusted_or_ambiguous_selections(self):
        for request in [[], None, {'runner_oses': ['self-hosted']},
                        {'runner_oses': ['ubuntu-latest']}, {'groups': ['all']},
                        {'groups': ['finalize\nother=value']},
                        {'runner_oses': 'macos-15'}, {'groups': None},
                        {'runner_oses': []}, {'groups': []},
                        {'runner_oses': ['macos-15', 'macos-15']},
                        {'groups': ['camp', 'camp']}, {'groups': [False]},
                        {'runner_oses': [['macos-15']]}]:
            with self.subTest(request=request), self.assertRaises(ValueError):
                ci_matrix.build_matrix(request)

    def test_actions_output_is_one_exact_json_line(self):
        with tempfile.TemporaryDirectory() as temp:
            request, output = Path(temp) / 'request.json', Path(temp) / 'output'
            request.write_text(json.dumps({'runner_oses': ['macos-15'], 'groups': ['finalize']}))
            output.write_bytes(b'existing=retained\n')
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(ci_matrix.main(['--request', str(request)]), 0)
            self.assertEqual(output.read_bytes(), b'existing=retained\nmatrix={"os":["macos-15"],"group":["finalize"]}\n')
            self.assertEqual(json.loads(stdout.getvalue()), {'os': ['macos-15'], 'group': ['finalize']})

    def test_invalid_request_does_not_publish_matrix(self):
        with tempfile.TemporaryDirectory() as temp:
            request, output = Path(temp) / 'request.json', Path(temp) / 'output'
            for source in ['{"groups":[]}', '{"groups":["camp"],"groups":["finalize"]}']:
                request.write_text(source)
                with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(ci_matrix.main(['--request', str(request)]), 2)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
