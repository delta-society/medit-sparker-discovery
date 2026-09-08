"""Synthetic KPI comparisons; not actual participant outcomes."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kpi
import plan


def sample():
    k = kpi.template()
    k.update(primary_seat=1, rationale='합성: 검토 부담을 줄여 유효 산출 증가를 시험',
             causal_chain=['검토시간 투입', '품질 통과 보고서', '확보 시간을 미처리 보고서에 사용'],
             output_unit='보고서 건', quality_rule='동일 필수항목·정확성 검사',
             realization_plan='미처리 보고서에 실제 사용하는지 확인', financial_link='추가 비용·매출 미확인')
    k['metrics'] = [dict(name=n, formula=f, unit=u, direction=d, target='기준선 후 설정',
                         target_status='unknown', basis='합성 시험용 제안') for n,f,u,d in [
        ('노동생산성','품질 통과 산출/총 사람시간','건/사람시간','increase'),
        ('품질 통과율','통과 산출/전체 산출','비율','maintain')]]
    k['measurement_plan'] = dict(source='합성 fixture', collector='시험 코드', window='동일 길이의 전후 기간', pairing='동일 업무 구성', frequency='시험 때')
    k['comparability'] = {key:True for key in k['comparability']}
    for name, hours in [('before',10),('after',5)]:
        k[name] = dict(kind='measured', window='합성 '+name, source='합성 시험 fixture — 실제 실측 아님',
                       accepted_output=90, total_output=100, labor_hours=hours,
                       actual_used_output=None, cost=None)
    return k


class KpiTests(unittest.TestCase):
    def test_increase(self):
        r=kpi.compare(sample()); self.assertEqual(r['status'],'increased')
        self.assertEqual(r['before_rate'],9); self.assertEqual(r['after_rate'],18)
        self.assertAlmostEqual(r['change_percent'],100)
        self.assertIn('이익 실현 미확인',r['financial_conclusion'])

    def test_unknown_not_zero(self):
        k=kpi.template(); self.assertEqual(kpi.compare(k)['status'],'measurement_pending')
        k['before']['labor_hours']=0
        with self.assertRaises(ValueError): kpi.validate(k)

    def test_quality_failure_even_if_faster(self):
        k=sample();k['after']['accepted_output']=70
        self.assertEqual(kpi.compare(k)['status'],'quality_failed')

    def test_incomparable(self):
        for flag in sample()['comparability']:
            for v in [False,None]:
                with self.subTest(flag=flag,v=v):
                    k=sample();k['comparability'][flag]=v
                    self.assertEqual(kpi.compare(k)['status'],'not_comparable')

    def test_zero_denominator(self):
        for field in ['labor_hours','total_output']:
            k=sample();k['before'][field]=0;k['before']['accepted_output']=0
            self.assertEqual(kpi.compare(k)['status'],'invalid_denominator')

    def test_zero_baseline_no_percent(self):
        k=sample();k['before']['accepted_output']=0
        r=kpi.compare(k);self.assertEqual(r['status'],'increased');self.assertIsNone(r['change_percent'])

    def test_no_false_measured_claim(self):
        for kind in ['self_report','synthetic']:
            k=sample();k['before']['kind']=kind
            self.assertEqual(kpi.compare(k)['status'],'provisional_increased')

    def test_unchanged_and_decrease(self):
        k=sample();k['after']['labor_hours']=10
        self.assertEqual(kpi.compare(k)['status'],'unchanged')
        k['after']['labor_hours']=20
        self.assertEqual(kpi.compare(k)['status'],'decreased')

    def test_invalid_numbers_counts_and_seats(self):
        for v in [-1, float('nan'), float('inf'), True]:
            k=sample();k['after']['labor_hours']=v
            with self.assertRaises(ValueError): kpi.validate(k)
        k=sample();k['after']['actual_used_output']=101
        with self.assertRaises(ValueError): kpi.validate(k)
        k=sample();k['primary_seat']=10
        with self.assertRaises(ValueError): kpi.validate(k)

    def test_complete_can_have_no_measurements(self):
        k=sample();k['before']=kpi.template()['before'];k['after']=kpi.template()['after']
        kpi.validate(k,True);self.assertEqual(kpi.compare(k)['status'],'measurement_pending')

    def test_legacy_fixture_and_new_revision(self):
        root=Path(__file__).parent/'fixtures'/'legacy-kpi'
        record=plan.Store(root).load('case-legacy')
        self.assertNotIn('kpi',record['plan'])
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp).resolve()/'cases';shutil.copytree(root,target)
            store=plan.Store(target);old=(target/'case-legacy/r000001/plan.md').read_bytes()
            p=copy.deepcopy(record['plan']);p['kpi']=sample()
            result=store.write('case-legacy','update',plan=p,expected=record['revision'],reason='합성 KPI 보완')
            self.assertEqual(store.load('case-legacy')['plan']['kpi'],p['kpi'])
            self.assertIn('100%',plan.markdown(result))
            self.assertEqual((target/'case-legacy/r000001/plan.md').read_bytes(),old)

    def test_cli_and_persisted_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();p=plan.template();p['submission']={'text':'합성 KPI 시험','source':'fixture'};p['kpi']=sample()
            store=plan.Store(root/'cases');store.write('case-kpi','new',plan=p)
            inp=root/'cases/case-kpi/r000001/plan.json'
            proc=subprocess.run([sys.executable,str(Path(kpi.__file__)),'evaluate','--input',str(inp),'--json'],capture_output=True,text=True, encoding='utf-8')
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['status'],'increased')
            self.assertIn('KPI 설정과 생산력', (inp.parent/'plan.md').read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
