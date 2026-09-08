"""Synthetic PDF lifecycle, escaping, offline rendering and release checks."""
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_plan import complete, confirmation
from plan import Store, markdown
import pdf_export as pdf
from pdf_browser import PdfError, browser_candidates, print_pdf, wait_for_page


class PdfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name).resolve() / '한글 경로')
        self.draft = self.store.write('sample', 'new', plan=complete())
        self.record = self.store.write('sample', 'finalize', expected=1, confirmation=confirmation(self.draft))

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_preserves_finalization_retry_and_corruption(self):
        before = (self.store.case_path('sample') / 'r000002' / 'plan.json').read_bytes()
        with patch.object(pdf, 'print_pdf', side_effect=PdfError('timeout', 'test')):
            result = pdf.export_pdf(self.store, 'sample', 2)
        self.assertEqual(result['code'], 'timeout')
        self.assertEqual(self.store.load('sample'), self.record)
        self.assertFalse(list(self.store.root.rglob('*.pdf')))
        with patch.object(pdf, 'print_pdf', return_value=(b'%PDF-1.4\nsynthetic\n%%EOF', {'ok': True})) as render:
            success = pdf.export_pdf(self.store, 'sample', 2)
            self.assertEqual(success['status'], 'ready')
            self.assertTrue(pdf.export_pdf(self.store, 'sample', 2)['reused'])
            self.assertEqual(render.call_count, 1)
            Path(success['path']).write_bytes(b'corrupt')
            self.assertEqual(pdf.export_pdf(self.store, 'sample', 2)['status'], 'failed')
            self.assertEqual(render.call_count, 1)
        self.assertEqual((self.store.case_path('sample') / 'r000002' / 'plan.json').read_bytes(), before)

    def test_cli_finalize_defers_pdf_until_explicit_request(self):
        case = 'cli-finalize'
        draft = self.store.write(case, 'new', plan=complete())
        confirm = self.store.root / 'confirmation.json'
        confirm.write_text(json.dumps(confirmation(draft)), encoding='utf-8')
        env = dict(os.environ, SPARKER_PDF_BROWSER=str(self.store.root / 'missing-browser'))
        run = subprocess.run([sys.executable, str(Path(pdf.__file__).with_name('plan.py')),
                              '--root', str(self.store.root), 'finalize', case,
                              '--expected-revision', '1', '--confirmation', str(confirm)],
                             env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['status'], 'finalized')
        self.assertEqual(result['pdf']['status'], 'not_requested')
        self.assertFalse((self.store.root / '.pdf-exports').exists())
        retry = subprocess.run([sys.executable, str(Path(pdf.__file__).with_name('plan.py')),
                                '--root', str(self.store.root), 'pdf', case,
                                '--expected-revision', '2'], env=env, capture_output=True,
                               text=True, encoding='utf-8', check=True)
        self.assertEqual(json.loads(retry.stdout)['code'], 'browser_missing')
        self.assertEqual(self.store.load(case)['revision'], 2)

    def test_draft_busy_and_old_revision(self):
        self.assertEqual(pdf.export_pdf(self.store, 'sample', 1)['status'], 'failed')
        base = self.store.root / '.pdf-exports/sample/r000002'
        base.mkdir(parents=True)
        (base / '.lock').mkdir()
        self.assertEqual(pdf.export_pdf(self.store, 'sample', 2)['code'], 'busy')
        (base / '.lock').rmdir()
        self.store.write('sample', 'reopen', expected=2, reason='test')
        with patch.object(pdf, 'print_pdf', return_value=(b'%PDF-1.4\n%%EOF', {'ok': True})):
            self.assertEqual(pdf.export_pdf(self.store, 'sample', 2)['status'], 'ready')
        self.assertEqual(self.store.load('sample')['revision'], 3)

    def test_payload_preserves_body_and_escapes_untrusted_html(self):
        self.record['plan']['user_result']['result'] = '</script><script>alert(1)</script>'
        document = pdf.make_html(self.record, {'fonts.css': '', 'print.css': '', 'render.js': ''})
        payload = document.split('type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(payload)['markdown'], markdown(self.record))
        self.assertNotIn('<script>alert', document)
        self.assertIn("connect-src 'none'", document)
        self.assertIn('파일 취합', json.loads(payload)['diagrams'][0]['source'])

    def test_devtools_waits_for_initial_blank_page(self):
        target = {'type': 'page', 'url': 'about:blank', 'webSocketDebuggerUrl': 'ws://127.0.0.1:1234/devtools/page/test'}
        replies = []
        for data in [[], [target]]:
            response = Mock(status=200)
            response.read.return_value = json.dumps(data).encode()
            connection = Mock()
            connection.getresponse.return_value = response
            replies.append(connection)
        with patch('pdf_browser.http.client.HTTPConnection', side_effect=replies), patch('pdf_browser.time.sleep'):
            self.assertEqual(wait_for_page(1234, Mock(poll=lambda: None), float('inf')), target)
        self.assertTrue(all(connection.close.called for connection in replies))

    def test_browser_paths_and_bundle_integrity(self):
        paths = browser_candidates({'PROGRAMFILES': 'C:/Program Files'}, 'win32')
        self.assertTrue(any('Edge' in str(path) for path in paths))
        self.assertTrue(any('Chrome' in str(path) for path in browser_candidates({}, 'darwin')))
        self.assertEqual(browser_candidates({'SPARKER_PDF_BROWSER': 'relative'}, 'linux'), [])
        bundle, fingerprint = pdf.assets()
        self.assertEqual(len(fingerprint), 64)
        self.assertIn('data:', bundle['fonts.css'])

    @unittest.skipUnless(os.environ.get('SPARKER_PDF_TEST_BROWSER'), 'opt-in actual browser')
    def test_actual_browser_valid_and_invalid_diagrams(self):
        bundle, _ = pdf.assets()
        document = pdf.make_html(self.record, bundle)
        raw, obs = print_pdf(document, '<span></span>', browser=os.environ['SPARKER_PDF_TEST_BROWSER'])
        self.assertTrue(raw.startswith(b'%PDF-'))
        self.assertEqual(obs['diagrams'], 1)
        bad = document.replace('flowchart TD', 'badDiagram TD')
        with self.assertRaises(PdfError) as failure:
            print_pdf(bad, '<span></span>', browser=os.environ['SPARKER_PDF_TEST_BROWSER'])
        self.assertEqual(failure.exception.code, 'diagram')

if __name__ == '__main__':
    unittest.main()
