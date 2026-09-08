#!/usr/bin/env python3
"""Read audit receipts, compare native AR responses against the tested renderer.
Does not call an LLM, authenticate, or modify runtime state. Checks AR and ST output contracts.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin/scripts'))
from example import ar_example, st_example


def verify(root):
    checks=[]
    for name,turn,posted,aligned in [('ar-unknown',1,'unknown','unknown'),('ar-posted',1,'yes','yes'),('ar-unposted',1,'no','yes'),('ar-unknown',2,'yes','yes'),('st-unknown',1,None,None)]:
        p=root/name
        r=json.loads((p/f'turn-{turn}-result.json').read_text())
        events=[json.loads(x) for x in (p/f'turn-{turn}.jsonl').read_text().splitlines() if x.strip()]
        commands=[]
        for event in events:
            for block in event.get('message',{}).get('content',[]):
                if isinstance(block,dict) and block.get('type')=='tool_use' and block.get('name')=='Bash':
                    commands.append(block.get('input',{}).get('command',''))
        expected=(st_example('10','20','3') if name=='st-unknown' else ar_example('600','300',posted,aligned,'2026-09-01','2026-09-07','EUR'))['markdown']
        flag='--quantity' if name=='st-unknown' else '--sap-open'
        used=any('example.py' in c and flag in c for c in commands)
        exact=r.get('result','').strip()==expected.strip()
        record=dict(case=name,turn=turn,is_error=r.get('is_error'),duration_ms=r.get('duration_ms'),helper_called=used,exact_response=exact,no_plan_written=not (p/'.sparker-discovery').exists())
        record['pass']=not record['is_error'] and used and exact and record['no_plan_written']
        checks.append(record)
    return checks

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('audit',type=Path);a=p.parse_args()
    rows=verify(a.audit)
    print(json.dumps(rows,ensure_ascii=False,indent=2))
    sys.exit(0 if all(r['pass'] for r in rows) else 1)
