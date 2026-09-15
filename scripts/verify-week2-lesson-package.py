#!/usr/bin/env python3
"""Exercise final ZIP's real record CLI. Synthetic data, NOT model/UI acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def verify(package):
    package = Path(package).resolve()
    with tempfile.TemporaryDirectory(prefix='sparker-lesson-') as tmp:
        root = Path(tmp).resolve()
        plugin = root/'plugin'
        with zipfile.ZipFile(package) as z:
            # This is the locally built allowlisted release, never participant intake.
            assert z.testzip() is None
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(plugin)
        assert (plugin/'references/week2-lesson.md').is_file()
        project = root/'실습 폴더'; project.mkdir()
        plan = project/'기획.md'
        plan.write_text('# 합성 시험 기획\n문자열 앞뒤 공백 정리 결과를 로컬 화면으로 확인한다.\n', encoding='utf-8')
        original = plan.read_bytes()
        source = project/'input.json'
        state = {'summary':'합성 시험: 로컬 문자열 정리', 'feature':'', 'scope_confirmation':'',
                 'environment':'', 'structure':'', 'desired_change':'', 'change_confirmation':'',
                 'stage':'bootstrap', 'next_action':'제품 생성', 'blockers':[], 'evidence':[],
                 'lesson':{'phase':'bootstrap','waiting_for':'none','product_path':'','local_url':'',
                           'workstream':'','acceptance_criteria':[],'learner_observation':''}}
        helper = plugin/'scripts/implementation.py'
        def command(*args):
            proc = subprocess.run([sys.executable,str(helper),'--project',str(project),*args],text=True,capture_output=True)
            assert proc.returncode == 0, proc.stderr+proc.stdout
            return proc.stdout
        def save(): source.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
        save(); command('new','lesson-test','--plan',str(plan),'--input',str(source))
        state['stage']='spec';state['lesson']['phase']='spec';state['next_action']='실제 제품 설명'
        save();command('update','lesson-test','--expected-revision','1','--input',str(source))
        state['feature']='입력 문자열 → 공백 정리 → 화면 결과'
        state['scope_confirmation']='합성 회귀시험 발화: 이 흐름으로 진행'
        state['lesson']['workstream']=state['feature']
        state['lesson']['acceptance_criteria']=['앞뒤 공백 제거, 내부 공백 유지']
        state['stage']='workstream';state['lesson']['phase']='workstream'
        save();command('update','lesson-test','--expected-revision','2','--input',str(source))
        state['stage']='paused';state['lesson']['waiting_for']='instructor'
        state['next_action']='실습② 시작 안내 대기'
        save();command('update','lesson-test','--expected-revision','3','--input',str(source))
        # A new process reads the latest persisted phase and waiting boundary.
        resumed=json.loads(command('show','lesson-test'))
        assert resumed['state']['lesson']['waiting_for']=='instructor',resumed
        assert resumed['state']['lesson']['workstream']==state['feature']
        state['stage']='baseline';state['lesson']['phase']='baseline'
        state['lesson']['waiting_for']='none';state['next_action']='대표 입력 실행'
        save();command('update','lesson-test','--expected-revision','4','--input',str(source))
        report=project/'중간 보고서.md'
        command('export','lesson-test','--output',str(report))
        assert report.is_file() and report.stat().st_size
        assert plan.read_bytes()==original
        receipt={'result':'PASS','scope':'final ZIP CLI storage/resume/export; synthetic, no model/UI acceptance',
                 'package':str(package),'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
                 'checks':['unpack','bootstrap without invented confirmation','spec','workstream selection',
                           'instructor pause','new-process resume','baseline transition','export','immutable source plan']}
        print(json.dumps(receipt,ensure_ascii=False,indent=2))
        return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');a=p.parse_args();verify(a.package)
