"""Adversarial storage regressions; all plans and confirmations are synthetic."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_plan import p, complete, confirmation
from test_linkage import linked, linked_confirmation


class StorageRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.store = p.Store(self.base / 'plans')

    def tearDown(self):
        self.tmp.cleanup()

    def test_newline_lifecycle_and_existing_bytes(self):
        for mode, factory, confirm in [('legacy', complete, confirmation), ('linked', linked, linked_confirmation)]:
            for index, newline in enumerate(['\n', '\r\n', '\r']):
                with self.subTest(mode=mode, newline=repr(newline)):
                    case = f'{mode}-{index}'
                    plan = factory()
                    value = '합성 첫 줄' + newline + '둘째 줄'
                    plan['user_result']['result'] = value
                    plan['workflow'][0]['output'] = value
                    if mode == 'linked':
                        plan['linkage']['upstream']['basis'] = value
                    first = self.store.write(case, 'new', plan=plan)
                    folder = self.store.case_path(case) / 'r000001'
                    snapshots = {x: x.read_bytes() for x in folder.iterdir()}
                    self.assertEqual(self.store.load(case), first)
                    plan['next_action']['action'] = value
                    draft = self.store.write(case, 'update', expected=1, reason=value, plan=plan)
                    conf = confirm(draft)
                    conf['quote'] += newline + '합성 확인'
                    final = self.store.write(case, 'finalize', expected=2, confirmation=conf)
                    self.assertEqual(self.store.load(case), final)
                    target = self.base / (case + '.md')
                    self.store.export(case, target)
                    self.assertEqual(target.read_bytes(), p.markdown(final).encode('utf-8'))
                    self.store.write(case, 'reopen', expected=3, reason='합성 수정 요청')
                    self.assertEqual(self.store.load(case)['revision'], 4)
                    for path, raw in snapshots.items():
                        self.assertEqual(path.read_bytes(), raw)

    def test_large_input_rejected_before_publication_and_can_retry(self):
        for case, char in [('ascii', 'A'), ('korean', '가')]:
            plan = linked()
            old = self.store.write(case, 'new', plan=plan)
            big = copy.deepcopy(plan)
            big['open_questions'] = ['']
            room = 1_999_950 - len(json.dumps(big, ensure_ascii=False).encode())
            big['open_questions'] = [char * (room // len(char.encode()))]
            source = self.base / (case + '.json')
            source.write_text(json.dumps(big, ensure_ascii=False), encoding='utf-8')
            parsed = p.read_json(source)  # Input really passes the public 2MB limit.
            with self.assertRaisesRegex(p.PlanError, '저장 레코드'):
                self.store.write(case, 'update', expected=1, reason='합성 크기 경계', plan=parsed)
            self.assertEqual(self.store.load(case), old)
            self.assertEqual([x.name for x in self.store.case_path(case).iterdir()], ['r000001'])
            good = self.store.write(case, 'update', expected=1, reason='합성 정상 재시도', plan=plan)
            self.assertEqual(self.store.load(case), good)

    def test_record_byte_limit_exact_boundary(self):
        fixed = datetime(2026, 9, 8, tzinfo=timezone.utc)
        for char in ['A', '가']:
            plan = linked()
            plan['open_questions'] = [char * 50]
            # Fixed clock makes the serialized envelope identical in fresh stores.
            with patch.object(p, 'datetime') as clock:
                clock.now.return_value = fixed
                sample_store = p.Store(self.base / ('sample-' + str(ord(char))))
                sample_store.write('boundary', 'new', plan=plan)
                size = (sample_store.case_path('boundary') / 'r000001/plan.json').stat().st_size
                for delta in [-1, 0, 1]:
                    with self.subTest(char=char, limit_delta=delta), patch.object(p, 'MAX_JSON_BYTES', size + delta):
                        store = p.Store(self.base / f'limit-{ord(char)}-{delta}')
                        if delta < 0:
                            with self.assertRaises(p.PlanError):
                                store.write('boundary', 'new', plan=plan)
                            self.assertEqual(store.revisions('boundary'), [])
                        else:
                            r = store.write('boundary', 'new', plan=plan)
                            self.assertEqual(store.load('boundary'), r)

    def test_finalize_envelope_overflow_leaves_draft_usable(self):
        old = self.store.write('finalize-size', 'new', plan=linked())
        conf = linked_confirmation(old)
        conf['quote'] = '합성' * 400_000
        with self.assertRaisesRegex(p.PlanError, '저장 레코드'):
            self.store.write('finalize-size', 'finalize', expected=1, confirmation=conf)
        self.assertEqual(self.store.load('finalize-size'), old)
        final = self.store.write('finalize-size', 'finalize', expected=1, confirmation=linked_confirmation(old))
        self.assertEqual(self.store.load('finalize-size'), final)

    def test_corrupted_staged_files_never_publish(self):
        old = self.store.write('staging', 'new', plan=linked())
        original_fsync = p.os.fsync
        calls = []
        def corrupt_after_sync(fd):
            original_fsync(fd)
            calls.append(fd)
            if len(calls) == 2:
                pending = next(self.store.case_path('staging').glob('.pending-*'))
                with (pending / 'plan.md').open('ab') as handle:
                    handle.write(b'SYNTHETIC CORRUPTION')
        with patch.object(p.os, 'fsync', side_effect=corrupt_after_sync):
            with self.assertRaisesRegex(p.PlanError, 'Markdown/JSON'):
                self.store.write('staging', 'update', plan=old['plan'], expected=1, reason='합성 손상 주입')
        self.assertEqual(self.store.load('staging'), old)
        self.assertEqual([x.name for x in self.store.case_path('staging').iterdir()], ['r000001'])
        self.store.write('staging', 'update', plan=old['plan'], expected=1, reason='합성 재시도')


if __name__ == '__main__':
    unittest.main()
