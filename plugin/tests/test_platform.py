"""Native CLI encoding/path contracts, without relying on the host's UTF-8 default."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_plan import p, SCRIPT


class PlatformTests(unittest.TestCase):
    def test_cli_stdout_stderr_are_utf8_under_legacy_codepages(self):
        for encoding in ['cp1252', 'cp949', 'ascii']:
            env = dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING=encoding)
            cases = [('plan.py', ['template', '--linked'], 0),
                     ('plan.py', ['show', 'missing-case'], 2),
                     ('submission.py', ['--example', 'standard-time', '--linked'], 0),
                     ('example.py', ['st', '--quantity', '10', '--setup', '20', '--per-unit', '3', '--json'], 0),
                     ('kpi.py', ['template'], 0)]
            with tempfile.TemporaryDirectory() as tmp:
                for script, args, code in cases:
                    with self.subTest(encoding=encoding, script=script, args=args):
                        result = subprocess.run([sys.executable, str(SCRIPT.parent / script), *args],
                                                cwd=tmp, env=env, capture_output=True)
                        self.assertEqual(result.returncode, code, result.stderr.decode('utf-8', errors='replace'))
                        value = json.loads((result.stdout if code == 0 else result.stderr).decode('utf-8'))
                        self.assertIsInstance(value, dict)

    def test_bom_input_and_unicode_path_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve() / '한글 사용자 & space'
            base.mkdir()
            source = base / '초안.json'
            plan = p.template(linked=True)
            source.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8-sig')
            env = dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING='cp1252')
            root = base / '실습 기록'
            for args in [['new', 'case-platform', '--input', str(source)], ['resume', 'case-platform']]:
                result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(root), *args],
                                        env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            self.assertEqual(p.Store(root).load('case-platform')['plan'], plan)
            self.assertTrue(source.read_bytes().startswith(b'\xef\xbb\xbf'))


if __name__ == '__main__':
    unittest.main()
