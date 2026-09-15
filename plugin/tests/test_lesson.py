"""Optional lesson metadata: synthetic fixtures and real local CLI calls."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import implementation as impl

LEGACY_KINDS = ('environment', 'execution', 'change', 'normal', 'exception', 'second_input')


def legacy():
    return dict(summary='합성 기획', feature='공백 정리', scope_confirmation='사용자 선택',
                environment='', structure='', desired_change='', change_confirmation='',
                stage='environment', next_action='환경 확인', blockers=[], evidence=[])


def bootstrap() -> dict:
    s = legacy()
    s.update(feature='', scope_confirmation='', stage='bootstrap', lesson=dict(
        phase='bootstrap', waiting_for='none', product_path='', local_url='', workstream='',
        acceptance_criteria=[], learner_observation=''))
    return s


class LessonTests(unittest.TestCase):
    def test_schema_and_scope_boundary(self):
        impl.validate_state(legacy())
        impl.validate_state(bootstrap())
        s = bootstrap(); s['stage'] = s['lesson']['phase'] = 'spec'
        impl.validate_state(s)
        for phase in ('bootstrap', 'spec'):
            paused = bootstrap(); paused['stage'] = 'paused'
            paused['lesson'].update(phase=phase, waiting_for='learner')
            impl.validate_state(paused)
        invalid = []
        for field in ('summary', 'next_action'):
            s = bootstrap(); s[field] = ''; invalid.append(s)
        for field, value in [('feature', '선택됨'), ('stage', 'workstream'), ('extra', '')]:
            s = bootstrap(); s[field] = value; invalid.append(s)
        for field, value in [('phase', 'spec'), ('phase', 'unknown'), ('waiting_for', 'agent'),
                             ('product_path', None), ('acceptance_criteria', 'text'),
                             ('acceptance_criteria', [1]), ('extra', ''), ('workstream', '선택됨')]:
            s = bootstrap(); s['lesson'][field] = value; invalid.append(s)
        s = bootstrap(); del s['lesson']; invalid.append(s)
        s = bootstrap(); s['lesson'] = None; invalid.append(s)
        s = bootstrap(); del s['lesson']['learner_observation']; invalid.append(s)
        s = legacy(); s['scope_confirmation'] = ''; invalid.append(s)
        s = bootstrap(); s['feature'] = ' '; invalid.append(s)
        for s in invalid:
            with self.subTest(state=s), self.assertRaises(impl.PlanError):
                impl.validate_state(s)
        for phase in ('workstream', 'baseline', 'improve', 'verify', 'demo'):
            s = legacy(); s['lesson'] = dict(bootstrap()['lesson'], phase=phase)
            s['stage'] = phase if phase in ('workstream', 'baseline', 'demo') else 'test'
            impl.validate_state(s)

    def test_optional_evidence_does_not_change_package_requirements(self):
        s = legacy()
        s.update(environment='python', structure='app.py', desired_change='trim', change_confirmation='선택')
        s['evidence'] = [dict(kind=k, outcome='pass') for k in LEGACY_KINDS]
        self.assertTrue(impl.ready(s, []))
        for kind in ('browser', 'replay', 'baseline', 'demo'):
            self.assertIn(kind, impl.KINDS)
        for required in LEGACY_KINDS:
            missing = copy.deepcopy(s)
            missing['evidence'] = [e for e in s['evidence'] if e['kind'] != required]
            missing['evidence'] += [dict(kind=k, outcome='pass') for k in ('browser', 'replay', 'baseline', 'demo')]
            self.assertFalse(impl.ready(missing, []))
        s.update(feature='', scope_confirmation='', stage='bootstrap', lesson=bootstrap()['lesson'])
        self.assertFalse(impl.ready(s, []))

    def test_cli_progression_pause_resume_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            plan = project / 'plan.md'; plan.write_text('# 합성 기획', encoding='utf-8')
            original = plan.read_bytes()
            inp = project / 'state.json'
            helper = Path(impl.__file__).resolve()
            def cli(*args):
                result = subprocess.run([sys.executable, str(helper), '--project', str(project), *args],
                                        capture_output=True, text=True, encoding='utf-8', stdin=subprocess.DEVNULL)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            s = bootstrap()
            inp.write_text(json.dumps(s), encoding='utf-8')
            r = cli('new', 'lesson', '--plan', str(plan), '--input', str(inp))
            first_path = project / '.sparker-implementation/lesson/r000001.json'
            first = first_path.read_bytes()
            for stage, phase, waiting in [('spec', 'spec', 'learner'), ('workstream', 'workstream', 'none'),
                                           ('paused', 'workstream', 'instructor'), ('baseline', 'baseline', 'none')]:
                s['stage'] = stage
                s['lesson'].update(phase=phase, waiting_for=waiting, product_path='product',
                                   local_url='http://localhost:3000', acceptance_criteria=['입력 결과를 확인한다'],
                                   learner_observation='합성 관찰: 화면 확인')
                if phase != 'spec':
                    s.update(feature='공백 정리', scope_confirmation='합성 학습자 선택')
                    s['lesson']['workstream'] = '입력 개선'
                inp.write_text(json.dumps(s), encoding='utf-8')
                r = cli('update', 'lesson', '--expected-revision', str(r['revision']), '--input', str(inp))
                shown = cli('show', 'lesson')
                self.assertEqual(shown['state'], s)
                self.assertFalse(shown['ready_for_local_package'])
            # Optional evidence is append-only and hash checked, like legacy kinds.
            evidence = project / 'observation.txt'; evidence.write_text('synthetic evidence', encoding='utf-8')
            s['evidence'] = [dict(kind=k, command='synthetic observation', input='sample', expected='result',
                                  observed='synthetic evidence', exit_code=None, outcome='pass',
                                  path=evidence.name, sha256=impl.sha(evidence.read_bytes()))
                             for k in ('browser', 'replay', 'baseline', 'demo')]
            inp.write_text(json.dumps(s), encoding='utf-8')
            cli('update', 'lesson', '--expected-revision', str(r['revision']), '--input', str(inp))
            out = project / 'lesson.md'
            self.assertEqual(cli('export', 'lesson', '--output', str(out))['state'], 'local_report_only')
            report = out.read_text(encoding='utf-8')
            for value in ('baseline', 'none', 'product', 'http://localhost:3000', '입력 개선',
                          '입력 결과를 확인한다', '합성 관찰: 화면 확인'):
                self.assertIn(value, report)
            self.assertEqual(first_path.read_bytes(), first)
            self.assertEqual(plan.read_bytes(), original)
            evidence.write_text('tampered', encoding='utf-8')
            self.assertTrue(cli('show', 'lesson')['evidence_findings'])

    def test_old_record_bytes_hash_chain_and_report_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = impl.Store(Path(tmp).resolve(), 'legacy')
            store.folder.mkdir(parents=True)
            # Version-1 fixture written without passing through the new save validator.
            old = dict(version=1, revision=1, previous=None, source={'name': 'plan.md'}, state=legacy())
            data = (impl.canonical(old) + '\n').encode('utf-8')
            path = store.folder / 'r000001.json'; path.write_bytes(data)
            before_report = ('\n\n'.join([
                '# 2주차 구현 기록', '',
                '로컬 기록이며 사람 발화·실행 진위를 인증하지 않습니다. 업로드/업무 효과 증거가 아닙니다.', '',
                '## 기획 요약', '합성 기획', '## 오늘의 기능', '공백 정리',
                '## 환경', '', '## 구조', '', '## 선택한 변경', '', '## 실행과 시험',
                '## 막힌 점', '## 다음 행동', '환경 확인']) + '\n').encode('utf-8')
            self.assertEqual(impl.report(old), before_report)
            self.assertEqual(store.load(), old)
            self.assertNotIn('lesson', store.show()['state'])
            s = legacy(); s['stage'] = 'paused'
            updated = store.save(s, expected=1)
            self.assertEqual(updated['previous'], impl.digest(old))
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(impl.report(old), before_report)
            self.assertNotIn('학습 진행'.encode(), before_report)
            # Upgrading an existing task is optional and never rewrites old revisions.
            s['lesson'] = dict(bootstrap()['lesson'], phase='workstream', waiting_for='instructor')
            store.save(s, expected=2)
            self.assertEqual(store.load()['state'], s)
            self.assertEqual(path.read_bytes(), data)
            path.write_bytes(data.replace('환경 확인'.encode(), '변경된 행동'.encode()))
            with self.assertRaises(impl.PlanError):
                store.load()


if __name__ == '__main__':
    unittest.main()
