"""Release allowlist and extracted runtime tests; no real private inputs."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_package', REPO / 'scripts/build-package.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve() / '실습 QA'
        self.base.mkdir()
        self.source = self.base / 'source'
        for folder in ['plugin', 'examples', 'docs']:
            shutil.copytree(REPO / folder, self.source / folder, ignore=shutil.ignore_patterns('__pycache__'))

    def tearDown(self):
        self.tmp.cleanup()

    def build(self):
        target = self.base / 'release.zip'
        with contextlib.redirect_stdout(io.StringIO()):
            builder.build(self.source, target)
        return target

    def test_private_files_excluded_and_extracted_helpers_work(self):
        for rel in ['plugin/.env', 'plugin/.sparker-discovery/case-test/r000001/plan.json',
                    'plugin/references/private.md', 'plugin/scripts/private.py', 'examples/private.md',
                    'plugin/old-release.zip', 'plugin/.sparker-submissions/week1.zip']:
            path = self.source / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('SYNTHETIC PRIVATE MARKER')
        target = self.build()
        dest = self.base / 'unpacked'
        with zipfile.ZipFile(target) as archive:
            expected = set(builder.PLUGIN_FILES) | {'examples/' + n for n in builder.EXAMPLE_FILES} | {'USER-GUIDE.md'}
            self.assertEqual(set(archive.namelist()), expected)
            self.assertTrue(all(b'SYNTHETIC PRIVATE MARKER' not in archive.read(n) for n in archive.namelist()))
            archive.extractall(dest)
        def run(script, *args):
            r = subprocess.run([sys.executable, str(dest / 'scripts' / script), *args], cwd=self.base,
                               capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)
        template = run('plan.py', 'template', '--linked')
        source = self.base / 'draft.json'
        source.write_text(json.dumps(template), encoding='utf-8')
        run('plan.py', 'new', 'package-case', '--input', str(source))
        self.assertEqual(run('plan.py', 'resume', 'package-case')['plan'], template)
        submission_zip = self.base / '.sparker-submissions' / 'package-case.zip'
        prepared = run('camp_submit.py', 'prepare', '--case', 'package-case',
                       '--expected-revision', '1', '--week', '1', '--output', str(submission_zip))
        self.assertEqual(prepared['state'], 'prepared_locally_not_submitted')
        self.assertFalse(prepared['manifest']['raw_session_records'])
        self.assertEqual(run('camp_submit.py', 'inspect', str(submission_zip))['sha256'], prepared['sha256'])
        for name in ['product-compliance', 'spec-policy', 'weekly-report', 'standard-time']:
            result = run('submission.py', '--example', name, '--linked')
            self.assertEqual(Path(result['submission']['source']).parent, dest / 'examples')
        self.assertEqual(run('example.py', 'ar', '--sap-open', '600', '--receipt', '300',
                             '--posted', 'no', '--aligned', 'yes', '--json')['review_balance'], '300.00')

    def test_missing_required_file_fails_before_output(self):
        (self.source / 'plugin/references/conversation.md').unlink()
        with self.assertRaisesRegex(ValueError, 'release file missing'):
            self.build()
        self.assertFalse((self.base / 'release.zip').exists())

    def test_release_symlinks_rejected_including_parent_examples_and_guide(self):
        for index, rel in enumerate(['plugin/scripts/plan.py', 'plugin/references', 'examples/weekly-report.md', 'docs/plugin-guide.md']):
            with self.subTest(path=rel):
                path = self.source / rel
                backup = self.base / f'original-{index}'
                path.rename(backup)
                try:
                    path.symlink_to(backup, target_is_directory=backup.is_dir())
                except OSError as exc:
                    backup.rename(path)
                    if getattr(exc, 'winerror', None) == 1314:
                        self.skipTest('Windows symlink privilege unavailable')
                    raise
                with self.assertRaisesRegex(ValueError, 'linked release path'):
                    self.build()
                path.unlink()
                backup.rename(path)
        self.assertFalse((self.base / 'release.zip').exists())


if __name__ == '__main__':
    unittest.main()
