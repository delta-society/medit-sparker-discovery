#!/usr/bin/env python3
"""Build standalone native Claude Code plugin ZIP; no install or network."""
from pathlib import Path
import argparse,hashlib,json,zipfile

# Exact release inputs: never discover files from a developer's working directory.
PLUGIN_FILES = (
    '.claude-plugin/plugin.json', 'skills/plan/SKILL.md', 'skills/submit/SKILL.md',
    'references/conversation.md', 'references/data-contract.md',
    'references/implementation-example.md', 'references/objective-linkage.md',
    'references/kpi-design.md',
    'scripts/pdf_browser.py', 'scripts/pdf_export.py', 'scripts/pdf_presentation.py',
    'assets/pdf/render.js', 'assets/pdf/fonts.css', 'assets/pdf/print.css',
    'assets/pdf/manifest.json', 'assets/pdf/THIRD_PARTY_NOTICES.md',
    'scripts/plan.py', 'scripts/linkage.py', 'scripts/submission.py',
    'scripts/example.py', 'scripts/kpi.py', 'scripts/portable.py', 'scripts/camp_submit.py',
)
EXAMPLE_FILES = ('README.md', 'product-compliance.md', 'spec-policy.md',
                 'weekly-report.md', 'standard-time.md')

def release_file(root, relative):
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('linked release path not allowed: ' + str(path))
    if not path.is_file():
        raise ValueError('release file missing: ' + str(path))
    return path

def build(root, output):
    root=Path(root).resolve();output=Path(output).resolve()
    entries={name:release_file(root, 'plugin/'+name) for name in PLUGIN_FILES}
    entries.update({'examples/'+name:release_file(root, 'examples/'+name) for name in EXAMPLE_FILES})
    entries['USER-GUIDE.md']=release_file(root, 'docs/plugin-guide.md')
    if output in entries.values():raise ValueError('output must not replace a release input')
    # Read only approved files. Untracked notes, .env, practice records and tests
    # are not inspected or included, even when placed inside scripts/references.
    contents={name:path.read_bytes() for name,path in entries.items()}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in sorted(contents.items()):z.writestr(name,content)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert '.claude-plugin/plugin.json' in z.namelist()
    receipt={'path':str(output),'files':len(entries),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    print(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    build(Path(__file__).resolve().parents[1],a.output)
