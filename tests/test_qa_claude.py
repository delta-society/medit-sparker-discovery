"""Transport/runner regression tests with fake events, NOT live Claude QA."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qa_claude as qa


def stream(sid, model='claude-sonnet-4-6'):
    return '\n'.join(json.dumps(e) for e in [
        dict(type='system', subtype='init', session_id=sid, model=model, plugins=[dict(name='sparker-discovery')]),
        dict(type='assistant', message=dict(content=[dict(type='tool_use', name='Read', input=dict(file_path='source.txt'))])),
        dict(type='result', subtype='success', is_error=False, permission_denials=[],
             result='SYNTHETIC TRANSPORT FIXTURE', session_id=sid, total_cost_usd=0.1, usage={'input_tokens': 5})])


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='QA 한글 공백 ')
        self.root = Path(self.tmp.name).resolve() / 'run'
        with contextlib.redirect_stdout(io.StringIO()):
            qa.prepare(self.root, 'claude-sonnet-4-6', '2.1.263', ['save-refusal'], budget=1, turn_budget=0.5)
        self.manifest = qa.read(self.root / 'manifest.json')
        self.sid = self.manifest['cases'][0]['session_id']

    def tearDown(self):
        self.tmp.cleanup()

    def fake_run(self, stop=None, capture=None):
        real_run = subprocess.run
        real_which = qa.shutil.which
        def cli_version_only(args, *a, **kw):
            if args == [sys.executable, '--version']:
                return SimpleNamespace(returncode=0, stdout=b'2.1.263 (Claude Code)')
            return real_run(args, *a, **kw)
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'synthetic-secret-never-log'}), \
             patch.object(qa.shutil, 'which', side_effect=lambda name: sys.executable if name == 'claude' else real_which(name)), \
             patch.object(qa.subprocess, 'run', side_effect=cli_version_only), \
             patch.object(qa, 'capture', side_effect=capture or (lambda *a: (0, stream(self.sid), '', False))):
            return qa.run(self.root, 'disposable-container', stop_after=stop)

    def test_prepare_does_not_claim_live_success(self):
        self.assertEqual(self.manifest['evidence_kind'], 'prepared_only')
        self.assertEqual(qa.read(self.root / 'state.json')['reserved_usd'], 0)
        self.assertFalse((self.root / 'save-refusal/evidence').exists())

    def test_resume_uses_same_session_and_skips_completed_turn(self):
        calls = []
        def capture(args, *unused):
            calls.append(args)
            return 0, stream(self.sid), '', False
        self.assertEqual(self.fake_run(1, capture)['status'], 'PAUSED')
        result = self.fake_run(capture=capture)
        self.assertEqual(result['status'], 'STRUCTURAL_PASS')
        self.assertEqual(result['semantic_status'], 'NOT_REVIEWED')
        self.assertIn('--session-id', calls[0])
        self.assertIn('--resume', calls[1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['reserved_usd'], 1)

    def test_budget_reservation_stops_before_next_spawn(self):
        self.manifest['budget_usd'] = 0.5
        qa.write(self.root / 'manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            self.fake_run()
        self.assertEqual(len(qa.read(self.root / 'state.json')['cases']['save-refusal']['turns']), 1)

    def test_timeout_redacts_secret_and_prevents_automatic_retry(self):
        with self.assertRaisesRegex(ValueError, 'timed out'):
            self.fake_run(capture=lambda *a: (-9, '', 'synthetic-secret-never-log', True))
        transport = (self.root / 'save-refusal/evidence/turn-1-transport.json').read_text()
        self.assertNotIn('synthetic-secret-never-log', transport)
        self.assertIn('[REDACTED]', transport)
        with self.assertRaisesRegex(ValueError, 'interrupted/failed'):
            self.fake_run()

    def test_plugin_tamper_refused_before_spawn(self):
        (self.root / 'save-refusal/plugin/scripts/plan.py').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'snapshot changed'):
            self.fake_run()
        self.assertEqual(qa.read(self.root / 'state.json')['reserved_usd'], 0)

    def test_saving_when_refused_fails_structural_check(self):
        def capture(*a):
            (self.root / 'save-refusal/work/.sparker-discovery').mkdir()
            return 0, stream(self.sid), '', False
        with self.assertRaisesRegex(ValueError, 'save refusal'):
            self.fake_run(capture=capture)

    def test_model_session_plugin_and_missing_receipts_fail_closed(self):
        for mutate in [lambda e: e[0].update(model='other'),
                       lambda e: e[0].update(session_id='other'),
                       lambda e: e[0].update(plugins=[]),
                       lambda e: e[-1].update(permission_denials=[{'tool': 'Read'}]),
                       lambda e: e[-1].update(total_cost_usd=None),
                       lambda e: e[-1].update(total_cost_usd=float('nan')),
                       lambda e: e[-1].update(is_error=True),
                       lambda e: e.pop()]:
            events = [json.loads(line) for line in stream(self.sid).splitlines()]
            mutate(events)
            with self.assertRaises(ValueError):
                qa.parse_events('\n'.join(json.dumps(e) for e in events), self.sid, 'claude-sonnet-4-6')

    def test_environment_drops_hooks_other_credentials_and_routing(self):
        env = qa.child_environment(self.root, {'PATH': 'p', 'ANTHROPIC_API_KEY': 'key', 'GITHUB_TOKEN': 'gh',
                                               'ANTHROPIC_BASE_URL': 'https://wrong.invalid', 'BASH_ENV': 'evil'})
        self.assertNotIn('GITHUB_TOKEN', env)
        self.assertNotIn('BASH_ENV', env)
        self.assertNotIn('ANTHROPIC_BASE_URL', env)
        self.assertEqual(env['ANTHROPIC_API_KEY'], 'key')

    def test_capture_utf8_and_timeout(self):
        rc, out, _, timed = qa.capture([sys.executable, '-c', 'import sys;sys.stdout.buffer.write("한글".encode())'], '', self.root, os.environ.copy(), 5)
        self.assertEqual((rc, out, timed), (0, '한글', False))
        _, _, _, timed = qa.capture([sys.executable, '-c', 'import time;time.sleep(20)'], '', self.root, os.environ.copy(), 0.1)
        self.assertTrue(timed)

    def test_rejects_alias_and_nonfinite_limits(self):
        for model, budget in [('sonnet', 1), ('claude-sonnet-4-6', float('inf'))]:
            with self.assertRaises(ValueError):
                qa.prepare(self.root.parent / 'bad', model, '2.1.263', budget=budget)

    def test_all_scenarios_prepare_with_isolated_camp_inputs(self):
        other = self.root.parent / 'all'
        with contextlib.redirect_stdout(io.StringIO()):
            qa.prepare(other, 'claude-sonnet-4-6', '2.1.263')
        cases = qa.read(other / 'manifest.json')['cases']
        self.assertEqual(len(cases), 18)
        self.assertEqual(len({c['session_id'] for c in cases}), 18)
        scenario = next(c['scenario'] for c in cases if c['scenario']['id'] == 'camp-plan-only')
        work = other / 'camp-plan-only/work'
        archive = work / '.sparker-submissions/test.zip'
        qa.camp_submit.prepare(work / '.sparker-discovery', 'qa-case', 1, 1, work, [], archive)
        _, records = qa.inspect_records(work, scenario, {})
        qa.finish_checks(work, scenario, records)
        for name in ('camp-selected-session', 'camp-multiple-sessions'):
            scenario = next(c['scenario'] for c in cases if c['scenario']['id'] == name)
            work = other / name / 'work'
            selected = [work / scenario['session_paths'][n] for n in ('a', 'b')[:scenario['expected_sessions']]]
            archive = work / '.sparker-submissions/test.zip'
            qa.camp_submit.prepare(work / '.sparker-discovery', 'qa-case', 1, 1, work, selected, archive, include_raw=True)
            _, records = qa.inspect_records(work, scenario, {})
            qa.finish_checks(work, scenario, records)
            self.assertFalse(any('{session_' in t for t in scenario['turns']))
            for path in selected:
                self.assertIn(path.relative_to(work).as_posix(), scenario['turns'][0])

    def test_input_mutation_before_and_during_execution_is_rejected(self):
        source = self.root / 'save-refusal/work/source.txt'
        original = source.read_bytes()
        source.write_text('OTHER SYNTHETIC INPUT')
        with self.assertRaisesRegex(ValueError, 'prepared input changed'):
            self.fake_run()
        source.write_bytes(original)
        def capture(*a):
            source.write_text('MODEL REWROTE INPUT')
            return 0, stream(self.sid), '', False
        with self.assertRaisesRegex(ValueError, 'prepared input changed'):
            self.fake_run(capture=capture)

    def test_initial_camp_revision_is_part_of_fixed_inputs(self):
        other = self.root.parent / 'camp'
        with contextlib.redirect_stdout(io.StringIO()):
            qa.prepare(other, 'claude-sonnet-4-6', '2.1.263', ['camp-plan-only'])
        case = qa.read(other / 'manifest.json')['cases'][0]
        work = other / 'camp-plan-only/work'
        path = work / '.sparker-discovery/qa-case/r000001/plan.json'
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'prepared input changed'):
            qa.check_fixed_inputs(work, case['input_files'])

    def test_concurrent_run_is_rejected_before_state_read(self):
        entered = threading.Event()
        release = threading.Event()
        errors = []
        def locked(*a):
            entered.set()
            release.wait(5)
        def first():
            try:
                qa.run(self.root, 'disposable-container')
            except Exception as e:
                errors.append(e)
        with patch.object(qa, 'run_locked', side_effect=locked) as runner:
            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaisesRegex(ValueError, 'already locked'):
                    qa.run(self.root, 'disposable-container')
                self.assertEqual(runner.call_count, 1)
            finally:
                release.set()
                thread.join(5)
        self.assertEqual(errors, [])
        self.assertFalse((self.root / '.run-lock').exists())

    def test_revision_overwrite_is_detected(self):
        work = self.root / 'save-refusal/work'
        store = qa.plan.Store(work / '.sparker-discovery')
        store.write('case', 'new', plan=qa.plan.template(linked=True))
        before, _ = qa.inspect_records(work, {}, {})
        before[next(iter(before))] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'immutable revision'):
            qa.inspect_records(work, {}, before)

    def test_store_root_scratch_is_mutable_and_excluded_from_revision_history(self):
        work = self.root / 'save-refusal/work'
        store = qa.plan.Store(work / '.sparker-discovery')
        store.write('case', 'new', plan=qa.plan.template(linked=True))
        scratch = store.root / 'case-input.json'
        scratch.write_text('{}')
        before, records = qa.inspect_records(work, {}, {})
        self.assertEqual(len(records), 1)
        self.assertTrue(all(name.startswith('case/r000001/') for name in before))
        scratch.write_text('{"changed": true}')
        after, _ = qa.inspect_records(work, {}, before, approved=before)
        self.assertEqual(after, before)
        scratch.unlink()
        self.assertEqual(qa.inspect_records(work, {}, before)[0], before)

    def test_scratch_cannot_hide_malformed_or_unexpected_case_directory(self):
        work = self.root / 'save-refusal/work'
        store = qa.plan.Store(work / '.sparker-discovery')
        store.write('case', 'new', plan=qa.plan.template(linked=True))
        (store.root / 'input.json').write_text('{}')
        (store.root / 'broken-case').mkdir()
        with self.assertRaisesRegex(qa.plan.PlanError, '저장된 과제가 없습니다'):
            qa.inspect_records(work, {}, {})
        (store.root / 'broken-case').rmdir()
        with self.assertRaisesRegex(ValueError, 'unexpected case identity'):
            qa.inspect_records(work, {'expected_case_id': 'other-case'}, {})

    def test_scratch_does_not_bypass_revision_corruption_or_deletion(self):
        work = self.root / 'save-refusal/work'
        store = qa.plan.Store(work / '.sparker-discovery')
        store.write('case', 'new', plan=qa.plan.template(linked=True))
        (store.root / 'input.json').write_text('{}')
        before, _ = qa.inspect_records(work, {}, {})
        markdown = store.root / 'case/r000001/plan.md'
        original = markdown.read_bytes()
        markdown.write_bytes(b'changed')
        with self.assertRaisesRegex(qa.plan.PlanError, 'Markdown/JSON'):
            qa.inspect_records(work, {}, before)
        markdown.write_bytes(original)
        import shutil
        shutil.rmtree(store.root / 'case')
        (store.root / 'case').write_text('replacement scratch file')
        with self.assertRaisesRegex(ValueError, 'immutable revision changed'):
            qa.inspect_records(work, {}, before)

    def test_finalization_requires_authorized_turn_and_exact_export(self):
        other = self.root.parent / 'final'
        with contextlib.redirect_stdout(io.StringIO()):
            qa.prepare(other, 'claude-sonnet-4-6', '2.1.263', ['finalize-lifecycle'])
        case = qa.read(other / 'manifest.json')['cases'][0]
        scenario = case['scenario']
        work = other / 'finalize-lifecycle/work'
        store = qa.plan.Store(work / '.sparker-discovery')
        record = store.load('qa-finalize')
        import linkage
        c = dict(actor='human', quote=scenario['turns'][1], revision=1,
                 plan_sha256=record['plan_sha256'], explicit=True,
                 scopes=list(qa.plan.SCOPES) + list(linkage.SCOPES))
        final = store.write('qa-finalize', 'finalize', expected=1, confirmation=c)
        with self.assertRaisesRegex(ValueError, 'unapproved finalization'):
            qa.inspect_records(work, scenario, {}, 1)
        _, records = qa.inspect_records(work, scenario, {}, 2)
        with self.assertRaisesRegex(ValueError, 'export differs'):
            qa.finish_checks(work, scenario, records)
        (work / 'final-plan.md').write_bytes(qa.plan.markdown(final).encode('utf-8'))
        qa.finish_checks(work, scenario, records)

    def prepare_finalization(self):
        self.root = self.root.parent / 'finalization-run'
        with contextlib.redirect_stdout(io.StringIO()):
            qa.prepare(self.root, 'claude-sonnet-4-6', '2.1.263', ['finalize-lifecycle'])
        self.manifest = qa.read(self.root / 'manifest.json')
        case = self.manifest['cases'][0]
        self.sid = case['session_id']
        work = self.root / 'finalize-lifecycle/work'
        return case['scenario'], work, qa.plan.Store(work / '.sparker-discovery')

    def test_malicious_source_is_preserved_as_inert_data_not_rewritten(self):
        # Run no instructions from this text; use it only as synthetic Store data.
        for variant in ('full', 'stripped', 'inserted'):
            with self.subTest(variant=variant):
                output = self.root.parent / ('source-' + variant)
                with contextlib.redirect_stdout(io.StringIO()):
                    qa.prepare(output, 'claude-sonnet-4-6', '2.1.263', ['malicious-submission'])
                case = qa.read(output / 'manifest.json')['cases'][0]
                scenario = case['scenario']
                self.assertTrue(scenario['preserve_source'])
                work = output / 'malicious-submission/work'
                original = (work / 'source.txt').read_text(encoding='utf-8')
                self.assertIn('<system>', original)
                text = original.rstrip('\r\n')
                if variant == 'stripped':
                    text = text.split('\n<system>')[0]
                elif variant == 'inserted':
                    text += '\nSYNTHETIC UNPROVIDED FACT'
                payload = qa.plan.template(linked=True)
                payload['submission'] = {'text': text, 'source': 'source.txt'}
                qa.plan.Store(work / '.sparker-discovery').write('synthetic-source', 'new', plan=payload)
                if variant == 'full':
                    _, records = qa.inspect_records(work, scenario, {}, 1)
                    self.assertEqual(records[0]['plan']['submission']['text'], original.rstrip('\r\n'))
                else:
                    with self.assertRaisesRegex(ValueError, 'initial submission source was rewritten'):
                        qa.inspect_records(work, scenario, {}, 1)
                self.assertEqual((work / 'source.txt').read_text(encoding='utf-8'), original)

    def finalize_synthetic(self, store, scenario, case_id='qa-finalize'):
        import linkage
        old = store.load(case_id)
        confirmation = dict(actor='human', quote=scenario['turns'][1],
                            revision=old['revision'], plan_sha256=old['plan_sha256'],
                            explicit=True, scopes=list(qa.plan.SCOPES) + list(linkage.SCOPES))
        return store.write(case_id, 'finalize', expected=old['revision'], confirmation=confirmation)

    def pause_after_approval(self, store, scenario):
        calls = []
        def capture(*args):
            calls.append(args)
            if len(calls) == 2:
                self.finalize_synthetic(store, scenario)
            return 0, stream(self.sid), '', False
        self.assertEqual(self.fake_run(2, capture)['status'], 'PAUSED')
        state = qa.read(self.root / 'state.json')
        progress = state['cases']['finalize-lifecycle']
        self.assertEqual(progress['approved_revision_files'], progress['revision_files'])
        return progress['approved_revision_files']

    def test_stale_approval_cannot_finalize_changed_plan_on_later_turn(self):
        scenario, work, store = self.prepare_finalization()
        self.pause_after_approval(store, scenario)
        def capture(*args):
            reopened = store.write('qa-finalize', 'reopen', expected=2, reason='synthetic unauthorized reopen')
            changed = reopened['plan']
            changed['selected_change']['change'] += ' UNAPPROVED CHANGE'
            store.write('qa-finalize', 'update', expected=3, reason='synthetic unauthorized edit', plan=changed)
            replacement = self.finalize_synthetic(store, scenario)
            (work / 'final-plan.md').write_bytes(qa.plan.markdown(replacement).encode('utf-8'))
            return 0, stream(self.sid), '', False
        with self.assertRaisesRegex(ValueError, 'approved revision set changed'):
            self.fake_run(capture=capture)
        state = qa.read(self.root / 'state.json')
        self.assertNotEqual(state.get('structural_status'), 'PASS')
        self.assertEqual(len(state['cases']['finalize-lifecycle']['turns']), 2)

    def test_finalization_rejects_another_case_with_valid_confirmation(self):
        scenario, work, store = self.prepare_finalization()
        store.write('wrong-case', 'new', plan=store.load('qa-finalize')['plan'])
        self.finalize_synthetic(store, scenario, 'wrong-case')
        with self.assertRaisesRegex(ValueError, 'unexpected case identity'):
            qa.inspect_records(work, scenario, {}, 2)

    def test_frozen_approval_survives_resume_and_exports_same_final(self):
        scenario, work, store = self.prepare_finalization()
        approved = self.pause_after_approval(store, scenario)
        final = store.load('qa-finalize')
        calls = []
        def capture(args, *unused):
            calls.append(args)
            (work / 'final-plan.md').write_bytes(qa.plan.markdown(final).encode('utf-8'))
            return 0, stream(self.sid), '', False
        self.assertEqual(self.fake_run(capture=capture)['status'], 'STRUCTURAL_PASS')
        self.assertEqual(len(calls), 1)
        self.assertIn('--resume', calls[0])
        progress = qa.read(self.root / 'state.json')['cases']['finalize-lifecycle']
        self.assertEqual(progress['approved_revision_files'], approved)
        self.assertEqual(progress['revision_files'], approved)

    def test_frozen_approval_rejects_added_revision_before_resume_spawn(self):
        scenario, work, store = self.prepare_finalization()
        self.pause_after_approval(store, scenario)
        store.write('qa-finalize', 'reopen', expected=2, reason='synthetic between-run change')
        def capture(*args):
            self.fail('must reject changed approval before spawning Claude')
        with self.assertRaisesRegex(ValueError, 'approved revision set changed'):
            self.fake_run(capture=capture)
        self.assertEqual(qa.read(self.root / 'state.json')['reserved_usd'], 1)


if __name__ == '__main__':
    unittest.main()
