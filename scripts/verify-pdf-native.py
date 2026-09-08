#!/usr/bin/env python3
"""Native CI smoke: extracted release, opt-in PDF, retry, immutable ledger."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'plugin/scripts'), str(REPO / 'plugin/tests')]
from test_plan import complete, confirmation
from pdf_browser import find_browser


def main():
    out = REPO / 'native-pdf-results'
    out.mkdir(exist_ok=True)
    browser = find_browser()
    subprocess.run([sys.executable, str(REPO / 'scripts/build-package.py'),
                    '--output', str(out / 'plugin.zip')], check=True)
    install = out / '한글 설치 경로'
    with zipfile.ZipFile(out / 'plugin.zip') as archive:
        archive.extractall(install)
    root = out / '한글 작업 경로'
    source = out / 'input.json'
    source.write_text(json.dumps(complete(), ensure_ascii=False), encoding='utf-8')
    command = [sys.executable, '-X', 'utf8', str(install / 'scripts/plan.py'), '--root', str(root)]
    def run(*args):
        result = subprocess.run(command + list(args), check=True, capture_output=True,
                                text=True, encoding='utf-8')
        return json.loads(result.stdout)
    draft = run('new', 'native', '--input', str(source))
    confirm = out / 'confirmation.json'
    confirm.write_text(json.dumps(confirmation(draft)), encoding='utf-8')
    finalized = run('finalize', 'native', '--expected-revision', '1', '--confirmation', str(confirm))
    assert finalized['pdf']['status'] == 'not_requested', finalized
    assert not (root / '.pdf-exports').exists()
    requested = run('pdf', 'native', '--expected-revision', '2')
    assert requested['status'] == 'ready', requested
    pdf_path = Path(requested['path'])
    raw = pdf_path.read_bytes()
    assert raw.startswith(b'%PDF-') and len(raw) > 10000
    ledger = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in root.rglob('*') if p.is_file() and '.pdf-exports' not in p.parts}
    retry = run('pdf', 'native', '--expected-revision', '2')
    assert retry['status'] == 'ready' and retry['reused'], retry
    assert ledger == {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in root.rglob('*') if p.is_file() and '.pdf-exports' not in p.parts}
    (out / 'native.pdf').write_bytes(raw)
    receipt = {'platform': sys.platform, 'browser': str(browser), 'bytes': len(raw),
               'finalize_without_pdf': True, 'requested_pdf': True, 'retry_reused': True, 'ledger_unchanged': True}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    env = dict(os.environ, SPARKER_PDF_TEST_BROWSER=str(browser))
    subprocess.run([sys.executable, '-X', 'utf8', '-m', 'unittest',
                    'test_pdf.PdfTests.test_actual_browser_valid_and_invalid_diagrams', '-v'],
                   cwd=REPO / 'plugin/tests', env=env, check=True)


if __name__ == '__main__':
    main()
