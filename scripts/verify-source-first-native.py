#!/usr/bin/env python3
"""Structural native-replay checks; questions still require semantic review."""
import hashlib,json,re,sys
from pathlib import Path

def verify(audit, package):
    root=Path(audit); results=[]
    for turn in (1,2):
        r=json.loads((root/'st'/f'turn-{turn}-result.json').read_text())
        assert not r.get('is_error') and not r.get('permission_denials'), r
        results.append(r['result'])
    events=[json.loads(line) for line in (root/'st/turn-1.jsonl').read_text().splitlines() if line.strip()]
    calls=[c for e in events for c in e.get('message',{}).get('content',[]) if isinstance(c,dict) and c.get('type')=='tool_use']
    assert any(c.get('name')=='Bash' and 'submission.py' in c.get('input',{}).get('command','') and 'standard-time' in c['input']['command'] for c in calls), 'source helper not exercised'
    for token in ('4','8','라인','엑셀','가이드'):
        assert token in results[0], token
    assert not any(re.search(r'(?<![\d.])0\s*%',t) for t in results), 'unsupported zero rate'
    assert not (root/'st/.sparker-discovery').exists(), 'save refusal not respected'
    sha=hashlib.sha256(Path(package).read_bytes()).hexdigest()
    assert sha==(root/'package-sha256.txt').read_text().strip()
    report={'structural_checks':'PASS','native_turns':2,'sha256':sha,'question_semantics':'requires reviewer inspection of both final responses'}
    (root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
    for i,t in enumerate(results,1):print('\nTURN',i,'\n',t)

if __name__=='__main__':
    verify(sys.argv[1],sys.argv[2])
