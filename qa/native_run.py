"""Run explicit live QA request on a disposable native OS CI runner.

Credentials are supplied by the CI secret store only to the run step.
"""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import qa_claude as qa

request = qa.read(ROOT / 'qa/live-request.json')
group = os.environ.get('QA_GROUP', 'all')
selected = [s for s in request['scenarios'] if group == 'all' or
            (group == 'camp' and s.startswith('camp-')) or
            (group == 'finalize' and s == 'finalize-lifecycle') or
            (group == 'reuse' and s.startswith('reuse-')) or
            (group == 'planning' and not s.startswith(('camp-', 'reuse-')) and s != 'finalize-lifecycle')]
qa.require(selected, 'empty QA group')
output = Path(os.environ['RUNNER_TEMP']) / 'Discovery 한글 QA' / (request['run_id'] + '-' + group)
if sys.argv[1] == 'prepare':
    print(json.dumps(qa.prepare(output, request['model'], request['claude_version'],
          selected, request['budget_usd'], request['turn_budget_usd'], request['timeout_seconds']), ensure_ascii=False))
elif sys.argv[1] == 'run':
    print(json.dumps(qa.run(output, 'disposable-vm'), ensure_ascii=False))
elif sys.argv[1] == 'collect':
    # Only redacted evidence and manifest/state, never Claude's config/logins.
    target = ROOT / 'qa-artifacts'
    target.mkdir(exist_ok=True)
    scrub = qa.redactor(os.environ)
    for path in [output / 'manifest.json', output / 'state.json', *output.glob('*/evidence/*.json')]:
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(output)
        qa.write(target / relative, scrub(qa.read(path)))
    qa.write(target / 'source.json', dict(source_sha=os.environ['GITHUB_SHA'],
             run_id=os.environ['GITHUB_RUN_ID'], os=os.environ['RUNNER_OS'], group=group,
             artifact_scope='redacted synthetic QA evidence; no config or credential files'))
else:
    raise SystemExit('expected prepare, run or collect')
