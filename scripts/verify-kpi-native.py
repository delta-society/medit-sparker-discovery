#!/usr/bin/env python3
"""Verify real native Claude Code KPI receipts and immutable records, not mock model output."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugin/scripts'))
import plan
import kpi

p=argparse.ArgumentParser();p.add_argument('audit',type=Path);p.add_argument('package',type=Path)
a=p.parse_args();audit=a.audit.resolve()
sha=hashlib.sha256(a.package.read_bytes()).hexdigest()
assert sha==(audit/'package-sha256.txt').read_text().strip(),'native package differs from deliverable'
results={}
for case,turns in [('unknown',[1]),('compare',[1,2])]:
    for turn in turns:
        record=json.loads((audit/case/f'turn-{turn}-result.json').read_text())
        assert not record.get('is_error') and record.get('result'),record
        assert not record.get('permission_denials'),record.get('permission_denials')
        results[f'{case}-{turn}']=record['result']

snapshots={}
for case in ['unknown','compare']:
    store=plan.Store(audit/case/'.sparker-discovery')
    cases=[x for x in store.root.iterdir() if x.is_dir() and not x.name.startswith('.')]
    assert len(cases)==1,(case,cases)
    case_id=cases[0].name
    latest=store.load(case_id)
    assert latest['status']=='draft' and latest['confirmation'] is None
    records=[json.loads(x.read_text()) for x in sorted(cases[0].glob('r*/plan.json'))]
    assert all('kpi' in r['plan'] for r in records)
    snapshots[case]=[kpi.compare(r['plan']['kpi']) for r in records]
    if case=='unknown':
        k=latest['plan']['kpi']
        assert k['before']['kind']=='unknown' and k['after']['kind']=='unknown'
        assert k['before']['labor_hours'] is None and k['after']['labor_hours'] is None
        assert 1<=len(k['metrics'])<=3
        assert snapshots[case][-1]['status']=='measurement_pending'
    else:
        assert len(records)>=2
        assert snapshots[case][0]['status']=='provisional_increased'
        assert snapshots[case][0]['change_percent']==100.0
        assert snapshots[case][-1]['status']=='provisional_quality_failed'
        assert records[0]['plan']['kpi']['after']['accepted_output']==90
        assert records[-1]['plan']['kpi']['after']['accepted_output']==70
        assert all(r['plan']['kpi']['before']['kind']=='synthetic' and r['plan']['kpi']['after']['kind']=='synthetic' for r in records)

report={'status':'PASS','native_turns':len(results),'zip_sha256':sha,'snapshots':snapshots,
        'scope':'Synthetic education conversations and real local save/readback. No participant outcome claim.'}
(audit/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
