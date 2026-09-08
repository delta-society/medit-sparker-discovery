#!/usr/bin/env python3
"""Build standalone native Claude Code plugin ZIP; no install or network."""
from pathlib import Path
import argparse,hashlib,json,zipfile

def build(root, output):
    root=Path(root).resolve();output=Path(output).resolve()
    plugin=root/'plugin'
    if not (plugin/'.claude-plugin/plugin.json').is_file():raise ValueError('plugin manifest missing')
    output.parent.mkdir(parents=True,exist_ok=True)
    entries={}
    for p in plugin.rglob('*'):
        if p.is_symlink():raise ValueError('symlink not packaged: '+str(p))
        if p.is_file() and not any(x in p.parts for x in ['__pycache__','.pytest_cache']) and p.suffix!='.pyc':entries[str(p.relative_to(plugin)).replace('\\','/')]=p
    for p in (root/'examples').glob('*.md'):entries['examples/'+p.name]=p
    entries['USER-GUIDE.md']=root/'docs/plugin-guide.md'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,p in sorted(entries.items()):z.writestr(name,p.read_bytes())
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert '.claude-plugin/plugin.json' in z.namelist()
    receipt={'path':str(output),'files':len(entries),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    print(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    build(Path(__file__).resolve().parents[1],a.output)
