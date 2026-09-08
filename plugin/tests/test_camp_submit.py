"""Synthetic Camp submissions; no user transcripts, auth, hooks or network."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import camp_submit as camp
from plan import PlanError, Store, template


class CampSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / 'participant project'
        self.project.mkdir()
        self.root = self.project / '.sparker-discovery'
        self.store = Store(self.root)
        self.store.write('example-case', 'new', plan=template(linked=True))
        self.output = self.project / '.sparker-submissions' / 'week1.zip'

    def tearDown(self):
        self.tmp.cleanup()

    def session(self, directory=None, cwd=None, content='SYNTHETIC exercise', sid=None):
        sid = sid or str(uuid.uuid4())
        directory = directory or self.base / 'transcripts'
        directory.mkdir(exist_ok=True, parents=True)
        path = directory / (sid + '.jsonl')
        data = {'type': 'user', 'sessionId': sid, 'cwd': str(cwd or self.project),
                'message': {'role': 'user', 'content': content}}
        path.write_bytes((json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8'))
        return path

    def prepare(self, sessions=(), **kwargs):
        args = dict(root=self.root, case='example-case', expected_revision=1, week=1,
                    project=self.project, sessions=list(sessions), output=self.output,
                    include_raw=bool(sessions))
        args.update(kwargs)
        return camp.prepare(**args)

    def test_plan_only_private_inputs_excluded_and_status_truthful(self):
        (self.project / '.env').write_text('DO NOT COPY')
        self.session(content='DO NOT COPY CONVERSATION')
        result = self.prepare()
        self.assertEqual(result['state'], 'prepared_locally_not_submitted')
        self.assertEqual(result['manifest']['plan']['status'], 'draft')
        self.assertFalse(result['manifest']['raw_session_records'])
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(set(archive.namelist()), {'manifest.json', 'plan.md'})
            for name in archive.namelist():
                self.assertNotIn(b'DO NOT COPY', archive.read(name))
                self.assertNotIn(str(self.base).encode(), archive.read(name))
        if os.name == 'posix':
            self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_multiple_sessions_preserve_exact_bytes_and_unselected_are_excluded(self):
        first = self.session(content='합성 내용\r\n 1')
        second = self.session(content='합성 내용 2')
        ignored = self.session(content='UNSELECTED')
        # Preserve source newline convention without rewriting the records.
        second.write_bytes(second.read_bytes().replace(b'\n', b'\r\n'))
        result = self.prepare([first, second])
        self.assertEqual(len(result['manifest']['sessions']), 2)
        with zipfile.ZipFile(self.output) as archive:
            for path in [first, second]:
                self.assertEqual(archive.read('sessions/' + path.name), path.read_bytes())
            self.assertNotIn('sessions/' + ignored.name, archive.namelist())
        self.assertEqual(camp.inspect(self.output)['sha256'], result['sha256'])

    def test_identical_retries_are_byte_identical_different_content_does_not_overwrite(self):
        a, b = self.session(), self.session()
        first = self.prepare([b, a])
        before = self.output.read_bytes()
        second = self.prepare([a, b])
        self.assertTrue(second['reused'])
        self.assertEqual(first['sha256'], second['sha256'])
        self.session(sid=a.stem, content='CHANGED')
        with self.assertRaisesRegex(PlanError, '이미 있습니다'):
            self.prepare([a, b])
        self.assertEqual(self.output.read_bytes(), before)

    def test_stale_revision_fails_and_old_plan_bytes_remain(self):
        old = (self.root / 'example-case/r000001/plan.json').read_bytes()
        self.store.write('example-case', 'update', plan=template(linked=True), expected=1, reason='synthetic edit')
        with self.assertRaisesRegex(PlanError, '리비전이 바뀌었습니다'):
            self.prepare()
        self.assertFalse(self.output.exists())
        self.assertEqual((self.root / 'example-case/r000001/plan.json').read_bytes(), old)

    def test_raw_requires_explicit_selection_and_rejects_duplicates_or_other_project(self):
        a = self.session()
        for paths, kwargs in [([a], {'include_raw': False}), ([], {'include_raw': True}),
                              ([a, a], {}), ([self.session(cwd=self.base / 'other')], {})]:
            with self.subTest(paths=paths, kwargs=kwargs), self.assertRaises(PlanError):
                self.prepare(paths, **kwargs)
            self.assertFalse(self.output.exists())

    def test_missing_mixed_or_mismatched_session_metadata_rejected(self):
        path = self.session()
        original = path.read_bytes()
        relative_cwd = json.loads(original)
        relative_cwd['cwd'] = 'relative/path'
        alternatives = [b'{"type":"user"}\n',
                        original + original.replace(path.stem.encode(), str(uuid.uuid4()).encode()),
                        original.replace(path.stem.encode(), str(uuid.uuid4()).encode()),
                        json.dumps(relative_cwd).encode()]
        for data in alternatives:
            with self.subTest(data=data):
                path.write_bytes(data)
                with self.assertRaises(PlanError):
                    self.prepare([path])
                self.assertFalse(self.output.exists())

    def test_partial_jsonl_and_duplicate_keys_are_not_silently_dropped(self):
        path = self.session()
        original = path.read_bytes()
        for suffix in [b'{"message":', b'{"type":"user","type":"assistant"}\n', b'\xff\n', b'[]\n']:
            path.write_bytes(original + suffix)
            with self.assertRaisesRegex(PlanError, '번째 줄'):
                self.prepare([path])
            self.assertFalse(self.output.exists())

    def test_limits_fail_without_truncation_or_partial_artifact(self):
        path = self.session(content='x' * 10000)
        original = path.read_bytes()
        with patch.object(camp, 'MAX_ZIP', 100):
            with self.assertRaisesRegex(PlanError, '5 MiB'):
                self.prepare([path])
        with patch.object(camp, 'MAX_TOTAL', 10):
            with self.assertRaisesRegex(PlanError, '50 MiB'):
                self.prepare([path])
        with self.assertRaises(PlanError):
            camp.stable_read(path, 100)
        self.assertFalse(self.output.exists())
        self.assertEqual(path.read_bytes(), original)

    def test_secret_review_reports_categories_not_secret_values(self):
        secret = 'ghp_' + 'A' * 36
        path = self.session(content='SYNTHETIC TOKEN ' + secret)
        result = self.prepare([path])
        self.assertEqual(result['possible_secrets'][0]['kind'], 'github-token')
        self.assertNotIn(secret, json.dumps(result))
        with zipfile.ZipFile(self.output) as archive:
            self.assertIn(secret.encode(), archive.read('sessions/' + path.name))

    def test_symlinks_rejected_for_input_output_and_parent(self):
        path = self.session()
        linked = self.base / 'linked'
        try:
            linked.symlink_to(path.parent, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable')
            raise
        with self.assertRaises(PlanError):
            self.prepare([linked / path.name])
        output_link = self.base / 'output.zip'
        output_link.symlink_to(path)
        with self.assertRaises(PlanError):
            self.prepare(output=output_link)
        self.assertTrue(path.exists())

    def test_stat_and_fstat_ctime_semantics_can_differ(self):
        from types import SimpleNamespace
        path = self.session()
        expected = path.read_bytes()
        real_fstat = os.fstat
        def different_ctime(fd):
            value = real_fstat(fd)
            return SimpleNamespace(**{name: getattr(value, name) for name in
                                      ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')},
                                   st_ctime_ns=value.st_ctime_ns + 1000000)
        with patch.object(camp.os, 'fstat', different_ctime):
            self.assertEqual(camp.stable_read(path), expected)

    def test_changed_file_during_read_rejected(self):
        path = self.session()
        real_open = Path.open
        class MutatingReader:
            def __enter__(self):
                self.handle = real_open(path, 'rb')
                return self
            def __exit__(self, *args):
                self.handle.close()
            def read(self, limit):
                data = self.handle.read(limit)
                with real_open(path, 'ab') as writer:
                    writer.write(b'\n')
                return data
            def fileno(self):
                return self.handle.fileno()
        with patch.object(Path, 'open', lambda *a, **k: MutatingReader()):
            with self.assertRaisesRegex(PlanError, '읽는 동안'):
                camp.stable_read(path)

    def test_stat_and_fstat_timestamp_domains_can_differ(self):
        # Windows stat may report creation time while fstat reports change time.
        # Different domains are fine if both snapshots remain stable.
        from types import SimpleNamespace
        path = self.session()
        actual_fstat = os.fstat
        def handle_stat(fd):
            s = actual_fstat(fd)
            return SimpleNamespace(st_dev=s.st_dev, st_ino=s.st_ino, st_size=s.st_size,
                                   st_mtime_ns=s.st_mtime_ns, st_ctime_ns=s.st_ctime_ns + 1000)
        with patch.object(os, 'fstat', side_effect=handle_stat):
            self.assertEqual(camp.stable_read(path), path.read_bytes())

    def test_handle_timestamp_mutation_is_still_rejected(self):
        from types import SimpleNamespace
        path = self.session()
        actual_fstat = os.fstat
        count = 0
        def handle_stat(fd):
            nonlocal count
            count += 1
            s = actual_fstat(fd)
            return SimpleNamespace(st_dev=s.st_dev, st_ino=s.st_ino, st_size=s.st_size,
                                   st_mtime_ns=s.st_mtime_ns, st_ctime_ns=s.st_ctime_ns + count)
        with patch.object(os, 'fstat', side_effect=handle_stat):
            with self.assertRaisesRegex(PlanError, '읽는 동안'):
                camp.stable_read(path)

    def test_inspect_rejects_tamper_extra_file_duplicate_and_unsafe_paths(self):
        self.prepare()
        with zipfile.ZipFile(self.output) as archive:
            original = {n: archive.read(n) for n in archive.namelist()}
        for extra in ['../private.txt', 'plan.json', 'sessions/not-a-uuid.jsonl']:
            files = dict(original, **{extra: b'bad'})
            self.output.write_bytes(camp.make_zip(files))
            with self.assertRaises(PlanError):
                camp.inspect(self.output)
        files = dict(original, **{'plan.md': b'changed plan'})
        self.output.write_bytes(camp.make_zip(files))
        with self.assertRaisesRegex(PlanError, '해시 불일치'):
            camp.inspect(self.output)
        buffer = io.BytesIO()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(buffer, 'w') as archive:
                for name, data in original.items():
                    archive.writestr(name, data)
                archive.writestr('plan.md', b'duplicate')
        self.output.write_bytes(buffer.getvalue())
        with self.assertRaises(PlanError):
            camp.inspect(self.output)

    def test_candidate_listing_stays_in_selected_folder_no_content_read(self):
        directory = self.base / 'chosen'
        included = self.session(directory)
        self.session(directory / 'subagents')
        self.session(self.base / 'other')
        with patch.object(Path, 'open', side_effect=AssertionError('Must not read conversations')):
            result = camp.candidates(self.project, directory)
        self.assertEqual([x['path'] for x in result['sessions']], [str(included)])
        self.assertFalse(result['membership_verified'])

    def test_archive_inspection_checks_counts_and_supports_other_os_paths(self):
        path = self.session()
        self.prepare([path])
        with zipfile.ZipFile(self.output) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(files['manifest.json'])
        manifest['sessions'][0]['records'] += 1
        manifest['bundle_id'] = camp.sha(camp.json_bytes({k: v for k, v in manifest.items() if k != 'bundle_id'}))
        files['manifest.json'] = camp.json_bytes(manifest)
        self.output.write_bytes(camp.make_zip(files))
        with self.assertRaisesRegex(PlanError, '기록 수 불일치'):
            camp.inspect(self.output)
        for cwd in [r'C:\Users\synthetic\project', '/home/synthetic/project']:
            row = {'sessionId': path.stem, 'cwd': cwd, 'type': 'user'}
            self.assertEqual(camp.validate_session(json.dumps(row).encode(), path.stem), 1)

    def test_non_week_and_incorrect_plan_integrity_rejected(self):
        for week in [0, 5, True, '1']:
            with self.assertRaises(PlanError):
                self.prepare(week=week)
        (self.root / 'example-case/r000001/plan.md').write_text('tampered')
        with self.assertRaisesRegex(PlanError, '불일치'):
            self.prepare()


if __name__ == '__main__':
    unittest.main()
