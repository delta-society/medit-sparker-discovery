"""Prompt wiring and synthetic persistence; live dialogue has a separate receipt."""
import copy
from pathlib import Path
import tempfile
import unittest
from test_linkage import linked
from test_plan import p

ROOT = Path(__file__).resolve().parents[1]

class ReuseFlowTests(unittest.TestCase):
    def test_flow_is_loaded_and_not_a_time_survey(self):
        skill = (ROOT/'skills/plan/SKILL.md').read_text(encoding='utf-8')
        ref = (ROOT/'references/objective-linkage.md').read_text(encoding='utf-8')
        self.assertIn('축적·활용 가설 선제안', skill)
        self.assertIn('축적·활용 가설 선제안', ref)
        for token in ['ai_hypothesis', '아직 모름', 'non_goals', 'record_mapping', 'event_mapping', '이미 확정된 목표', '절감 시간 사용처']:
            self.assertIn(token, ref)

    def test_hypothesis_selection_and_unknown_survive_revisions(self):
        plan = linked(confirmed=False)
        plan['objective'].update(outcome='합성 제안: 유사 공정 근거를 활용한 ST 초안 검토',
            causal_relation='AI 가설: 공정 조건·실측값·수정 이유 축적 → 유사 사례 재사용 → 근거를 갖춘 ST 초안 검토',
            definition='유사 사례 근거를 확인하고 검토 완료한 신규 공정 ST 초안 건수', unit='건')
        plan.setdefault('facts', []).append(dict(id='reuse-hypothesis', kind='ai_hypothesis',
            text='합성 가설: 공정 조건과 실측값을 연결하면 유사 공정 ST 초안에 재사용 가능', source='합성 업무 설명에서 AI 추론'))
        plan['linkage']['measurement'].update(status='record_only', app='',
            metric_reference=plan['objective']['metric_reference'],
            event_mapping='합성 설계: 초안 검토 완료 시 참조 사례와 수정 이유 기록',
            record_mapping='합성 설계: 공정 ID·참조 사례 ID·추정값·검토 확정값·수정 이유 연결',
            dedupe='같은 검토 ID 중복 집계 제외; 수정 이력 유지',
            failure='자료 없는 추정과 검토 실패는 미확인/실패로 유지',
            basis='AI 활용 가설에서 도출한 기록 설계; 실제 수집 아님', acquisition_ids=[])
        plan['selected_change']['non_goals'].append('선택되지 않은 편차 분석 기능')
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as d:
            store = p.Store(Path(d)/'plans')
            first = store.write('reuse', 'new', plan=plan)
            old = (Path(d)/'plans/reuse/r000001/plan.json').read_bytes()
            unknown = copy.deepcopy(plan)
            unknown['open_questions'].append('합성 응답: 아직 모름 — 활용 가설은 미확정')
            second = store.write('reuse', 'update', expected=1, reason='합성 아직 모름', plan=unknown)
            self.assertEqual(second['status'], 'draft')
            self.assertEqual(second['plan']['objective']['status'], 'proposed')
            selected = copy.deepcopy(unknown)
            selected['selected_change']['change'] = '합성 선택: ST 초안 추정만 포함'
            selected['facts'].append(dict(id='reuse-choice', kind='human_confirmed', text='합성 테스트 선택: 초안 추정만', source='합성 참가자 응답; 실제 사람 증거 아님'))
            third = store.write('reuse', 'update', expected=2, reason='합성 단일 활용 선택', plan=selected)
            actual = store.load('reuse')
            self.assertEqual(actual, third)
            self.assertEqual(actual['plan']['facts'][-2]['kind'], 'ai_hypothesis')
            self.assertIsNone(actual['plan']['objective']['confirmation'])
            self.assertEqual(old, (Path(d)/'plans/reuse/r000001/plan.json').read_bytes())
            md = p.markdown(actual)
            for token in ['공정 조건', '참조 사례 ID', '수정 이유', '선택되지 않은 편차 분석 기능']:
                self.assertIn(token, md)
            with self.assertRaises(p.PlanError):
                p.validate_plan(actual['plan'], complete=True)

if __name__ == '__main__':
    unittest.main()
