"""Synthetic-only Week2 records, adversarial intake, and extracted CLI proof."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'plugin/scripts'))
import implementation as impl


def state():
    return dict(summary='합성 공백 정리 기획', feature='입력에서 출력까지',
                scope_confirmation='합성 테스트 확인', environment='', structure='',
                desired_change='', change_confirmation='', stage='environment',
                next_action='환경 확인', blockers=[], evidence=[])


class ImplementationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name).resolve() / '한글 실습'
        self.p.mkdir()
        self.plan = self.p / 'plan.md'
        self.plan.write_bytes('# 합성 기획\r\n문자열 정리\r\n'.encode())
        self.store = impl.Store(self.p, 'task-a')

    def tearDown(self):
        self.tmp.cleanup()

    def create(self):
        return self.store.save(state(), source=impl.intake(self.plan))

    def test_resume_revision_conflict_and_original_preservation(self):
        original = self.plan.read_bytes()
        r = self.create()
        first = (self.store.folder / 'r000001.json').read_bytes()
        s = state(); s['stage'] = 'paused'
        self.store.save(s, expected=1)
        self.assertEqual(self.store.show()['revision'], 2)
        self.assertFalse(self.store.show()['ready_for_local_package'])
        self.assertEqual(first, (self.store.folder / 'r000001.json').read_bytes())
        self.assertEqual(original, self.plan.read_bytes())
        with self.assertRaises(impl.PlanError):
            self.store.save(s, expected=1)
        with self.assertRaises(impl.PlanError):
            impl.package(self.store, ['plan.md'], self.p / 'no.zip')
        self.assertFalse((self.p / 'no.zip').exists())

    def test_duplicate_unknown_keys_and_lock(self):
        with self.assertRaises(impl.PlanError):
            impl.parse(b'{"a":1,"a":2}')
        s = state(); s['unknown'] = True
        with self.assertRaises(impl.PlanError):
            self.store.save(s, source={})
        self.create()
        (self.store.folder / '.lock').mkdir()
        with self.assertRaises(FileExistsError):
            self.store.save(state(), expected=1)
        self.assertTrue((self.store.folder / '.lock').is_dir())

    def test_pdf_requires_explicit_host_read_not_fake_text(self):
        pdf = self.p / 'plan.pdf'; pdf.write_bytes(b'%PDF-1.4\nsynthetic placeholder only')
        result = impl.intake(pdf)
        self.assertEqual(result['status'], 'needs_host_read')
        self.assertNotIn('text', result)
        inp = self.p / 'state.json'; inp.write_text(json.dumps(state()))
        r = subprocess.run([sys.executable, str(REPO/'plugin/scripts/implementation.py'), '--project', str(self.p), 'new', 'pdf-a', '--plan', str(pdf), '--input', str(inp)], capture_output=True)
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.p/'.sparker-implementation/pdf-a').exists())

    def archive(self, entries):
        path = self.p / 'intake.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, data in entries:
                z.writestr(name, data)
        return path

    def test_zip_selective_read_and_guards(self):
        z = self.archive([('기획/plan.md', '# 합성'), ('other.txt', 'not selected')])
        self.assertEqual(impl.intake(z)['members'], ['기획/plan.md'])
        self.assertEqual(impl.intake(z, '기획/plan.md')['text'], '# 합성')
        bad = ['../plan.md', '/plan.md', 'C:/plan.md', 'a\\plan.md', 'nested.zip', 'nested.docx', 'a/./plan.md']
        for name in bad:
            with self.subTest(name=name), self.assertRaises(impl.PlanError):
                impl.intake(self.archive([(name, 'bad')]))
        for entries in [[('plan.md','x'),('PLAN.md','y')], [('plan.md', 'a' * 100000)], [('plan.md', b'PK\x03\x04hidden')]]:
            with self.assertRaises(impl.PlanError):
                impl.intake(self.archive(entries))
        link = zipfile.ZipInfo('plan.md'); link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(impl.PlanError):
            impl.intake(self.archive([(link, 'target')]))
        with self.assertRaises(impl.PlanError):
            impl.intake(self.archive([(str(i)+'.md', 'x') for i in range(101)]))

    def test_submission_path_and_secret_guards(self):
        for name, data in [('a/.env.txt', b'x'), ('.git/a.py', b'x'), ('node_modules/a.js', b'x'), ('transcript.txt', b'x'), ('secret.py', b'x'), ('private.pem', b'x'), ('a.py', b'password="1234567890"'), ('a.py', b'ghp_' + b'A'*30), ('a.py', b'\x00')]:
            with self.subTest(name=name), self.assertRaises(impl.PlanError):
                impl.allowed(name, data)
        impl.allowed('src/main.py', b'print("synthetic")')
        target = self.p / 'link.md'
        try:
            target.symlink_to(self.plan)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        with self.assertRaises(impl.PlanError):
            impl.intake(target)
        with self.assertRaises(impl.PlanError):
            impl.put_new(self.plan, b'overwrite')

    def test_evidence_tamper_and_append_only(self):
        s = state()
        efile = self.p / 'run.txt'; efile.write_bytes(b'observed synthetic output')
        e = dict(kind='normal', command='synthetic command', input='synthetic input', expected='output', observed='output', exit_code=0, outcome='pass', path='run.txt', sha256=impl.sha(efile.read_bytes()))
        s['evidence'] = [e]
        self.store.save(s, source=impl.intake(self.plan))
        changed = copy.deepcopy(s); changed['evidence'] = []
        with self.assertRaises(impl.PlanError):
            self.store.save(changed, expected=1)
        efile.write_bytes(b'changed')
        self.assertTrue(self.store.show()['evidence_findings'])
        with self.assertRaises(impl.PlanError):
            self.store.save(s, expected=1)

    def test_latest_failure_and_chain_corruption(self):
        self.create()
        s = state(); s.update(environment='python', structure='one file', desired_change='trim', change_confirmation='synthetic')
        s['evidence'] = [dict(kind=k, outcome='pass') for k in impl.KINDS]
        self.assertTrue(impl.ready(s, []))
        s['evidence'].append(dict(kind='normal', outcome='fail'))
        self.assertFalse(impl.ready(s, []))
        self.store.save(state(), expected=1)
        p = self.store.folder/'r000001.json'
        p.write_bytes(p.read_bytes().replace('환경 확인'.encode(), '다른 행동'.encode()))
        with self.assertRaises(impl.PlanError):
            self.store.load()

    def test_extracted_package_actual_execution_smoke(self):
        spec = importlib.util.spec_from_file_location('week2_builder', REPO/'scripts/build-package.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        archive = self.p/'release.zip'; builder.build(REPO, archive)
        extracted = self.p/'plugin'
        with zipfile.ZipFile(archive) as z:
            z.extractall(extracted)
        helper = extracted/'scripts/implementation.py'
        def cli(*args):
            r = subprocess.run([sys.executable, str(helper), '--project', str(self.p), *args], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)
        for command in ('new','show','update','export','package','intake'):
            self.assertEqual(subprocess.run([sys.executable, str(helper), command, '--help'], capture_output=True).returncode, 0)
        inp = self.p/'state.json'; inp.write_text(json.dumps(state()))
        cli('new','task-a','--plan',str(self.plan),'--input',str(inp))
        first = (self.store.folder/'r000001.json').read_bytes()
        app = self.p/'app.py'
        app.write_text('import sys\nprint(sys.argv[1].strip())\n', encoding='utf-8')
        s = state(); s.update(environment='실제 Python subprocess', structure='app.py 입력→strip→stdout', desired_change='대문자로 출력', change_confirmation='합성 테스트 발화: 대문자 선택', stage='submit', next_action='로컬 파일 목록 검토')
        evidence = self.p/'evidence'; evidence.mkdir()
        cases = [('environment',[sys.executable,'--version'], 'Python'), ('execution',[sys.executable,str(app),' a '], 'a')]
        def run(kind, command, expected, code=0):
            r = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(r.returncode, code)
            self.assertIn(expected, r.stdout+r.stderr)
            path = evidence/(kind+'.txt')
            path.write_text('SYNTHETIC EXECUTION\n'+r.stdout+r.stderr, encoding='utf-8')
            s['evidence'].append(dict(kind=kind, command=' '.join(command), input=repr(command[2:]), expected=expected, observed=(r.stdout+r.stderr).strip(), exit_code=r.returncode, outcome='pass', path='evidence/'+path.name, sha256=impl.sha(path.read_bytes())))
        for kind, command, expected in cases:
            run(kind,command,expected)
        app.write_text('import sys\nif len(sys.argv) != 2:\n    print("missing input", file=sys.stderr)\n    sys.exit(2)\nprint(sys.argv[1].strip().upper())\n', encoding='utf-8')
        for kind, value, expected in [('change',' a ','A'),('normal',' b ','B'),('second_input',' c ','C')]:
            run(kind,[sys.executable,str(app),value],expected)
        run('exception',[sys.executable,str(app)],'missing input',2)
        inp.write_text(json.dumps(s))
        cli('update','task-a','--expected-revision','1','--input',str(inp))
        self.assertTrue(cli('show','task-a')['ready_for_local_package'])
        cli('export','task-a','--output',str(self.p/'report.md'))
        (self.p/'README.md').write_text('# SYNTHETIC ONLY\nRun: python3 app.py " a "\nExpected: A\n')
        files = ['app.py','README.md']+[e['path'] for e in s['evidence']]
        allow = self.p/'files.json'; allow.write_text(json.dumps(files))
        out = self.p/'week2.zip'; out2 = self.p/'week2-again.zip'
        result = cli('package','task-a','--files',str(allow),'--output',str(out))
        cli('package','task-a','--files',str(allow),'--output',str(out2))
        self.assertEqual(out.read_bytes(), out2.read_bytes())
        self.assertEqual(result['state'], 'prepared_locally_not_submitted')
        submitted = self.p/'submission'
        with zipfile.ZipFile(out) as z:
            self.assertEqual(set(z.namelist()), set(files)|{'implementation.md','manifest.json'})
            z.extractall(submitted)
        r = subprocess.run([sys.executable, str(submitted/'app.py'), ' new '], capture_output=True, text=True)
        self.assertEqual(r.stdout, 'NEW\n')
        self.assertEqual(first, (self.store.folder/'r000001.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
