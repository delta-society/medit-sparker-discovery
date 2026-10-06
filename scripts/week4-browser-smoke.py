#!/usr/bin/env python3
"""Synthetic isolated app + actual W4 CLI + browser approval + download readback.
Requires a built test app, and a confirmed case from week4-smoke.py.
Never creates participant records on production.
"""
import argparse,hashlib,json,os,subprocess,sys,tempfile,time,urllib.request,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--app',required=True);p.add_argument('--case',required=True);p.add_argument('--output',required=True)
a=p.parse_args();app=Path(a.app).resolve();case=Path(a.case).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
plugin=Path(__file__).resolve().parents[1]/'plugin'
for f in ['.env','.env.local','.env.production','.env.production.local']:assert not (app/f).exists()
seed=subprocess.run([str(app/'node_modules/.bin/tsx'),'tests/report-http-fixture.ts'],cwd=app,capture_output=True,text=True,check=True)
state=Path(seed.stdout.strip()).resolve();assert state.name.startswith('sparker-report-http-TEST-ONLY-')
env=json.loads((state/'environment.json').read_text());origin=env['SPARKER_ORIGIN'];assert origin=='http://127.0.0.1:3495'
credentials=json.loads((state/'credentials.json').read_text());serverlog=(state/'server.log').open('w')
server=subprocess.Popen(['node','scripts/start.mjs'],cwd=app,env={'HOME':os.environ['HOME'],'PATH':os.environ['PATH'],'NEXT_TELEMETRY_DISABLED':'1',**env},stdout=serverlog,stderr=subprocess.STDOUT)
try:
 deadline=time.monotonic()+30
 while True:
  assert server.poll() is None,'Test server stopped'
  try:
   if urllib.request.urlopen(origin+'/api/health',timeout=1).status==200:break
  except Exception:pass
  assert time.monotonic()<deadline,'Test server not ready';time.sleep(.1)
 with tempfile.TemporaryDirectory(prefix='sparker-w4-home-TEST-ONLY-') as temp_home:
  home=str(Path(temp_home).resolve())
  command=[sys.executable,str(plugin/'scripts/week4.py'),'submit','--root',str(case),'--submit','--origin',origin,'--local-test','--no-browser','--wait','0']
  childenv={**os.environ,'HOME':home}
  def run(rc):
   result=subprocess.run(command,env=childenv,capture_output=True,text=True,timeout=25)
   assert result.returncode==rc,result.stdout[-1500:]
   return json.loads(result.stdout)
  first=run(2);assert first['status']=='pending'
  private=Path(home)/'.config/sparker-report'/hashlib.sha256(origin.encode()).hexdigest()
  intent=next(json.loads(f.read_text()) for f in private.glob('*.json') if 'approval_url' in json.loads(f.read_text()))
  with sync_playwright() as pw:
   browser=pw.chromium.launch();ctx=browser.new_context(viewport={'width':1280,'height':1000});page=ctx.new_page()
   login=ctx.request.post(origin+'/api/login',data=credentials,headers={'Origin':origin});assert login.status==200
   page.goto(intent['approval_url']);button=page.get_by_role('button',name='터미널 연결에 동의하고 제출',exact=True);button.wait_for(timeout=15000)
   text=page.inner_text('body');assert '4주차' in text and 'final-code-and-report.zip' in text
   page.screenshot(path=str(out/'week4-connection.png'),full_page=True)
   button.click();page.get_by_text('승인했습니다.',exact=False).wait_for(timeout=15000)
   submitted=run(0);assert submitted['status']=='submitted' and submitted['receipt']['week']==4
   rows=ctx.request.get(origin+'/api/dashboard').json()['submissions'];assert len(rows)==1 and rows[0]['week']==4
   download=ctx.request.get(origin+'/api/files/'+rows[0]['id']);assert download.status==200
   assert hashlib.sha256(download.body()).hexdigest()==submitted['receipt']['sha256']
   assert (private/'device-week4.json').is_file() and not (private/'device.json').exists()
   assert (private/'device-week4.json').stat().st_mode&0o777==0o600
   repeated=run(0);assert repeated==submitted
   assert len(ctx.request.get(origin+'/api/dashboard').json()['submissions'])==1
   page.goto(origin+'/?view=learning');page.wait_for_load_state('networkidle');page.screenshot(path=str(out/'week4-submitted.png'),full_page=True)
   receipt={'synthetic_only':True,'real_cli':True,'real_browser_login_and_week4_approval':True,'pending_resumed':True,'repeat_no_duplicate':True,'week':4,'download_sha256_matches':True,'separate_week4_private_credential':True,'receipt':submitted['receipt']}
   (out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
   browser.close()
finally:
 server.terminate();server.wait(timeout=15);serverlog.close();shutil.rmtree(state)
