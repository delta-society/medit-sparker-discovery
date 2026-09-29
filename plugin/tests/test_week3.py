"""Deterministic ledger/CLI and real local fixture IO; NOT model or SaaS QA."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import week3 as w


class Week3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name).resolve() / '한글 실습'
        self.project.mkdir()
        self.store = w.Store(self.project, 'own-product')
        self.source = {'summary': '기존 주문 집계 업무', 'plan_ref': 'plan.md', 'product_ref': 'product.py'}
        self.store.write(source=self.source)
        self.run_id = 'trial-1'
        self.mode = 'local_rehearsal'

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, event):
        return self.store.write(event=event, expected=self.store.show()['revision'])

    def assessment(self, when='before'):
        for criterion in w.CRITERIA:
            self.add(dict(kind='assessment', when=when, criterion=criterion, judgment='아직 모름',
                          evidence='합성 로컬 시험만 관측; 운영 미확인', next_action='실사용 별도 확인'))

    def design(self):
        self.assessment()
        d = dict.fromkeys(w.DESIGN, '합성 시험의 구조 설명')
        d.update(kind='design', recipient='local-inbox', change_consent='테스트 fixture가 지정한 로컬 쓰기만 허용')
        self.add(d)

    def artifact(self, kind, payload, **extra):
        path = self.project / (kind + '.json')
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return dict(kind=kind, run=self.run_id, mode=self.mode, artifact=path.name,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(), observation='합성 로컬 실제 관측: ' + kind, **extra)

    def read_use(self):
        read = self.artifact('input_read', {'orders': [2, 3]})
        self.add(read)
        # Actual file read and processing, not a pre-computed expected output.
        values = json.loads((self.project / read['artifact']).read_text())['orders']
        use = self.artifact('product_use', {'total': sum(values)}, input_sha256=read['sha256'])
        self.add(use)
        return read, use

    def approve(self, use):
        self.add(dict(kind='output_approval', run=self.run_id, mode=self.mode, recipient='local-inbox',
                      content_sha256=use['sha256'], consent='합성 테스트의 local-inbox에 위 결과 파일을 쓰도록 허용'))

    def delivery(self, use):
        # This is a local mailbox, never a SaaS delivery claim.
        inbox = self.project / 'inbox.json'
        shutil.copyfile(self.project / use['artifact'], inbox)
        sent = self.artifact('output_sent', {'wrote': inbox.name, 'bytes': inbox.stat().st_size},
                             recipient='local-inbox', content_sha256=use['sha256'])
        self.add(sent)
        received_bytes = inbox.read_bytes()
        self.assertEqual(hashlib.sha256(received_bytes).hexdigest(), use['sha256'])
        received = self.artifact('output_received', {'read_back': inbox.name,
                                 'actual': json.loads(received_bytes), 'mode': 'local_rehearsal'},
                                 recipient='local-inbox', content_sha256=use['sha256'])
        return sent, received

    def finish(self):
        return self.add(dict(kind='finish', consent='합성 테스트의 결과와 운영 미확인을 검토함', next_action='실제 SaaS는 별도 승인 후 시험'))

    def test_premature_completion_and_design_require_all_six(self):
        with self.assertRaises(w.PlanError):
            self.finish()
        d = dict.fromkeys(w.DESIGN, 'x')
        with self.assertRaises(w.PlanError):
            self.add(dict(d, kind='design'))
        self.design()
        self.assessment('after')
        with self.assertRaises(w.PlanError):
            self.finish()

    def test_source_read_not_product_use(self):
        self.design()
        read = self.artifact('input_read', {'value': 4})
        r = self.add(read)
        self.assertFalse(r['evidence_chain_complete'])
        with self.assertRaises(w.PlanError):
            self.approve(read)
        wrong = self.artifact('product_use', {'total': 4}, input_sha256='0' * 64)
        with self.assertRaises(w.PlanError):
            self.add(wrong)
        self.assertNotIn('product_use', self.store.show()['state']['steps'])

    def test_no_send_without_exact_recipient_content_approval(self):
        self.design()
        _, use = self.read_use()
        event = self.artifact('output_sent', {'accepted': True}, recipient='local-inbox', content_sha256=use['sha256'])
        with self.assertRaises(w.PlanError):
            self.add(event)
        self.approve(use)
        for patch in ({'recipient': 'other-channel'}, {'content_sha256': '0' * 64}, {'mode': 'live'}):
            with self.assertRaises(w.PlanError):
                self.add(dict(event, **patch))
        self.add(event)
        self.assertFalse(self.store.show()['evidence_chain_complete'])

    def test_send_not_receipt_and_old_reassessment_invalidated(self):
        self.design()
        _, use = self.read_use()
        self.approve(use)
        sent, received = self.delivery(use)
        self.assessment('after')
        with self.assertRaises(w.PlanError):
            self.finish()
        copied = dict(sent, kind='output_received')
        with self.assertRaises(w.PlanError):
            self.add(copied)
        r = self.add(received)
        self.assertTrue(r['evidence_chain_complete'])
        self.assertEqual(r['state']['after'], {})
        with self.assertRaises(w.PlanError):
            self.finish()
        self.assessment('after')
        r = self.finish()
        self.assertTrue(r['learning_review_complete'])
        self.assertEqual(r['production_readiness'], 'not_certified')
        self.assertEqual(r['mode'], 'local_rehearsal')

    def test_resume_stale_revision_and_legacy_preservation(self):
        legacy = {'.sparker-discovery/case/r000001/plan.md': b'legacy week1\r\n',
                  '.sparker-implementation/case/r000001.json': b'{"legacy":2}\n',
                  'product.py': b'# learner original\n', 'plan.md': '원본'.encode()}
        for name, data in legacy.items():
            p = self.project / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        self.design()
        self.read_use()
        self.add(dict(kind='pause', blocker='Outlook 미연결', next_action='수신처 확인 하나'))
        resumed = w.Store(self.project, 'own-product').show()
        self.assertEqual(resumed['state']['next_action'], '수신처 확인 하나')
        self.assertEqual(set(resumed['state']['steps']), {'input_read', 'product_use'})
        with self.assertRaises(w.PlanError):
            self.store.write(event=dict(kind='pause', blocker='x', next_action='y'), expected=1)
        report = w.report(resumed).decode()
        self.assertIn('output_received: 미확인', report)
        self.assertIn('학습 검토 완료: False', report)
        for name, data in legacy.items():
            self.assertEqual((self.project / name).read_bytes(), data)

    def test_new_run_cannot_reuse_approval_or_mix_mode(self):
        self.design()
        _, use = self.read_use()
        self.approve(use)
        _, received = self.delivery(use)
        self.add(received)
        self.assessment('after')
        self.finish()
        self.run_id, self.mode = 'trial-live', 'live'
        read = self.artifact('input_read', {'new': 'input'})
        r = self.add(read)
        self.assertFalse(r['learning_review_complete'])
        self.assertEqual(list(r['state']['steps']), ['input_read'])
        self.assertEqual(r['state']['after'], {})
        with self.assertRaises(w.PlanError):
            self.add(dict(received, run=self.run_id, mode=self.mode))

    def test_tamper_incomplete_report_and_no_existing_output_overwrite(self):
        self.design()
        read, use = self.read_use()
        self.approve(use)
        _, received = self.delivery(use)
        self.add(received)
        self.assessment('after')
        self.finish()
        (self.project / read['artifact']).write_text('changed')
        r = self.store.show()
        self.assertFalse(r['learning_review_complete'])
        self.assertFalse(r['evidence_chain_complete'])
        self.assertIn('증거 누락/변경', w.report(r).decode())
        out = self.project / 'plan.md'
        out.write_text('original')
        with self.assertRaises(w.PlanError):
            w.put_new(out, w.report(r))
        self.assertEqual(out.read_text(), 'original')

    def test_credential_rejection_no_state_or_error_leak(self):
        samples = ['password=synthetic-password', 'Authorization: Bearer synthetic-auth',
                   'https://user:pw@example.invalid/doc', 'https://example.invalid/?token=synthetic',
                   'api_key=synthetic-value', 'Cookie: synthetic-cookie']
        for value in samples:
            with self.subTest(value=value), self.assertRaises(w.PlanError):
                self.add(dict(kind='pause', blocker=value, next_action='do not store'))
        self.assertEqual(self.store.show()['revision'], 1)
        self.design()
        event = self.artifact('input_read', {'password': 'synthetic-secret-value'})
        with self.assertRaises(w.PlanError):
            self.add(event)
        for path in self.store.folder.glob('*.json'):
            self.assertNotIn('synthetic-secret-value', path.read_text())

    def test_traversal_symlink_and_invalid_event_schema(self):
        self.design()
        event = self.artifact('input_read', {'safe': True})
        for change in ({'artifact': '../outside.json'}, {'extra': 'unknown'}, {'sha256': 'bad'}):
            with self.assertRaises((w.PlanError, ValueError)):
                self.add(dict(event, **change))
        linked = self.project / 'linked.json'
        try:
            linked.symlink_to(self.project / event['artifact'])
        except OSError:
            self.skipTest('symlink unavailable')
        with self.assertRaises(w.PlanError):
            self.add(dict(event, artifact=linked.name))

    def test_cli_resume_export_and_errors_do_not_echo_secrets(self):
        script = str(ROOT / 'scripts/week3.py')
        def run(*args):
            return subprocess.run([sys.executable, script, '--project', str(self.project), *args],
                                  capture_output=True, text=True, encoding='utf-8', stdin=subprocess.DEVNULL)
        out = run('show', 'own-product')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)['revision'], 1)
        report = self.project / 'unfinished.md'
        out = run('export', 'own-product', '--output', str(report))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('미평가', report.read_text(encoding='utf-8'))
        event_file = self.project / 'event.json'
        event_file.write_text('{"password":"never-echo-this"', encoding='utf-8')
        out = run('append', 'own-product', '--expected-revision', '1', '--input', str(event_file))
        self.assertEqual(out.returncode, 2)
        self.assertNotIn('never-echo-this', out.stdout + out.stderr)

    def test_skill_and_connector_contract(self):
        skill = (ROOT / 'skills/week3/SKILL.md').read_text(encoding='utf-8')
        for text in ('name: week3', '/sparker-discovery:week3', '자동 수정·입출력 연결·발송은 하지 않는다',
                     '한 장 PDF', '반론이 맞으면 판단', '전체 평가서', '.sparker-evaluation'):
            self.assertIn(text, skill)
        connectors = (ROOT / 'references/week3-connectors.md').read_text(encoding='utf-8')
        for text in ('Confluence', 'Outlook', 'Slack', '도구 목록/스키마', '자동 재전송 금지', '수신측'):
            self.assertIn(text, connectors)


if __name__ == '__main__':
    unittest.main()
