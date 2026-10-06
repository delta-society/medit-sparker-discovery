#!/usr/bin/env python3
"""Reproducible synthetic W4 actual execution + native one-page PDF smoke."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin/scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin/tests'))
import week4 as w
from test_week4 import selected
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
out=Path(a.output).absolute();out.mkdir(parents=True,exist_ok=False)
root,spec,feedback=selected(out)
code=Path(spec['code_root'])
before=subprocess.run([sys.executable,str(code/'app.py')],capture_output=True,text=True,check=True).stdout
# This fixture was explicitly selected by synthetic consent, not a real learner.
(code/'app.py').write_text("print('review required')\n",encoding='utf-8')
after=subprocess.run([sys.executable,str(code/'app.py')],capture_output=True,text=True,check=True).stdout
assert before=='draft\n' and after=='review required\n'
md=w.manifest(w.files(code,spec['files']));peer_digest=w.digest(md)
peer=out/'peer-recheck.txt';peer.write_text('합성 동료: 검토 필요 표시를 확인했습니다.\n',encoding='utf-8')
# Final change after the peer saw the first revision must not inherit their approval.
(code/'app.py').write_text("print('review required - final')\n",encoding='utf-8')
command=[sys.executable,str(code/'app.py')]
run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==0 and run.stdout=='review required - final\n'
log=out/'final-test.log';log.write_text(run.stdout+run.stderr,encoding='utf-8')
md=w.manifest(w.files(code,spec['files']))
result=dict(files=spec['files'],summary='합성 제품: 검토 필요 표시를 추가하고 최종 문구 보완',before=before.strip(),after=run.stdout.strip(),remaining='실제 참가자·업무 사용 미검증',tests=[dict(command='python3 app.py',exit_code=run.returncode,code_digest=w.digest(md),log=str(log),sha256=w.sha(log.read_bytes()))],peer=dict(status='checked',reviewer='합성 동료',same_peer=True,code_digest=peer_digest,source=str(peer),evidence=dict(source='peer',line_start=1,line_end=1,quote='검토 필요 표시를 확인했습니다.'),remaining='합성 답변이며 실제 동료 아님. 재수정본은 미확인'))
r=w.final(root,result);w.confirm(root,r['digest'],'합성 참가자: 최종 코드와 한 장 보고서 확인')
receipt=w.bundle(root);r,raw,metadata=w.current_bundle(root)
assert receipt['peer_matches_final'] is False
with w.zipfile.ZipFile(w.BytesIO(raw)) as z:
    assert set(z.namelist())=={'code/app.py','code/README.md','report.pdf','manifest.json'}
    assert not any(w.SECRET.search(z.read(n)) for n in ['code/app.py','code/README.md','manifest.json'])
summary=dict(synthetic_only=True,actual_before=before.strip(),actual_after=run.stdout.strip(),exit_code=run.returncode,root=str(root),bundle=str(root/('bundle-r%06d'%r['revision'])/'final-code-and-report.zip'),pdf=str(root/('bundle-r%06d'%r['revision'])/'report.pdf'),metadata=metadata,pdf_observation=receipt['observation'],peer_final_separated=True,source_and_pdf_hashes_verified=True,credentials_or_transcript_in_package=False)
(out/'smoke-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
