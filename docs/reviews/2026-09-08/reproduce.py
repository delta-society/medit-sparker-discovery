"""Reproduce reviewed defects using synthetic temporary data only.
Run from any cwd: python3 /path/to/repo/docs/reviews/2026-09-08/reproduce.py
Does not mutate product sources, existing plans, credentials or external services.
Creates /tmp-style temporary artifacts and leaves their path in stdout for inspection.
Assertions describe defects in reviewed main 8d1f705, not desired regression behavior.
"""
import copy, importlib.util, json, pathlib, shutil, subprocess, sys, tempfile
from unittest.mock import patch
REPO=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'plugin/tests'))
from test_plan import p
from test_linkage import linked, linked_confirmation
BASE=pathlib.Path(tempfile.mkdtemp(prefix='sparker-review-'))
results={}
def cli(root,*args):
    r=subprocess.run([sys.executable,str(REPO/'plugin/scripts/plan.py'),'--root',str(root),*map(str,args)],capture_output=True,text=True)
    return {'exit':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}
# Valid input becomes an unreadable committed revision.
root=BASE/'size'; s=p.Store(root); old=s.write('case-size','new',plan=linked())
big=copy.deepcopy(old['plan']); big['open_questions']=['']
size=len(json.dumps(big,ensure_ascii=False).encode()); big['open_questions']=['A'*(1_999_950-size)]
f=BASE/'large-input.json'; f.write_text(json.dumps(big,ensure_ascii=False),encoding='utf-8')
update=cli(root,'update','case-size','--input',f,'--expected-revision','1','--reason','synthetic size boundary test')
results['oversize']={'input_bytes':f.stat().st_size,'committed_record_bytes':(root/'case-size/r000002/plan.json').stat().st_size,'update':update,'show':cli(root,'show','case-size'),'r1_exists':(root/'case-size/r000001/plan.json').exists()}
# Standalone required acquisition work disappears from the only handoff artifact.
s=p.Store(BASE/'export'); plan=linked(bound=True)
marker='SYNTHETIC-RULE-ACQUISITION-REQUIRED'
plan['acquisition_tasks'].append(dict(id='rule-acquisition',what=marker,owner='test owner',method='obtain approved calculation rule',done_when='rule reviewed'))
r=s.write('case-export','new',plan=plan); r=s.write('case-export','finalize',expected=1,confirmation=linked_confirmation(r)); dest=BASE/'handoff.md';s.export('case-export',dest)
results['omitted_acquisition']={'finalized':r['status'],'task_in_json':marker in json.dumps(r),'task_in_export':marker in dest.read_text()}
# Packaging picks up ignored local files; only fake markers, no real secrets.
clone=BASE/'package-source'; shutil.copytree(REPO/'plugin',clone/'plugin',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(REPO/'examples',clone/'examples');(clone/'docs').mkdir();shutil.copy2(REPO/'docs/plugin-guide.md',clone/'docs/plugin-guide.md')
(clone/'plugin/.env').write_text('SYNTHETIC_ONLY=not-a-real-secret\n'); private=clone/'plugin/.sparker-discovery/case-synthetic/r000001';private.mkdir(parents=True);(private/'plan.json').write_text('{"synthetic":"private practice marker"}')
spec=importlib.util.spec_from_file_location('build',REPO/'scripts/build-package.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
mod.build(clone,BASE/'plugin.zip')
import zipfile
with zipfile.ZipFile(BASE/'plugin.zip') as z:
    results['package_leak']={'unexpected_entries':[n for n in z.namelist() if n.startswith('.env') or '.sparker-discovery' in n]}
# Deferred crash cleanup and hostile-path defenses are assessed against documented contract.
s=p.Store(BASE/'controls');r=s.write('case-control','new',plan=linked())
try:s.write('case-control','update',plan=r['plan'],expected=99,reason='stale')
except p.PlanError as e:results['stale_write_control']=str(e)
bad=copy.deepcopy(r['plan']);bad['objective']['definition']='changed without renewed confirmation'
try:p.validate_plan(bad,complete=True)
except p.PlanError as e:results['kpi_change_control']=str(e)
try:
    with patch.object(p.os,'fsync',side_effect=OSError('synthetic disk failure')):
        s.write('case-control','update',plan=r['plan'],expected=1,reason='failure injection')
except OSError:pass
results['write_failure_control']={'old_revision_readable':s.load('case-control')['revision']==1,'lock_left':(BASE/'controls/case-control/.lock').exists()}
# Blank linked template permanently forbids adding first source to submission field.
s=p.Store(BASE/'source'); r=s.write('case-source','new',plan=p.template(linked=True)); new=copy.deepcopy(r['plan']);new['submission']={'text':'synthetic first provided submission','source':'synthetic user message'}
try:s.write('case-source','update',plan=new,expected=1,reason='first source arrives')
except p.PlanError as e:results['late_source']=str(e)
# CRLF input survives validation but produces a committed unreadable Markdown revision.
root=BASE/'newline'; s=p.Store(root); old=s.write('case-newline','new',plan=linked())
updated=copy.deepcopy(old['plan']);updated['user_result']['result']='First line\r\nSecond line'
f=BASE/'crlf-input.json';f.write_text(json.dumps(updated,ensure_ascii=False),encoding='utf-8')
res=cli(root,'update','case-newline','--input',f,'--expected-revision','1','--reason','synthetic Windows multiline input')
results['crlf']={'update':res,'show':cli(root,'show','case-newline'),'committed_revision_exists':(root/'case-newline/r000002/plan.md').exists()}
assert results['oversize']['update']['exit']==2 and results['oversize']['show']['exit']==2
assert results['oversize']['input_bytes']<2_000_000<results['oversize']['committed_record_bytes']
assert results['crlf']['update']['exit']==2 and results['crlf']['show']['exit']==2
assert results['crlf']['committed_revision_exists']
assert len(results['package_leak']['unexpected_entries'])==2
assert results['write_failure_control']['old_revision_readable']
assert not results['write_failure_control']['lock_left']
results['base']=str(BASE)
(BASE/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
