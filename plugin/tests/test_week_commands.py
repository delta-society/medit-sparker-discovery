"""Static skill contract guards; not a substitute for live model dialogue QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WeekCommandTests(unittest.TestCase):
    def skill(self, name):
        return (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')

    def test_router_requires_week_and_never_runs_helper(self):
        router = self.skill('submit')
        for text in ('week1-submit/SKILL.md', 'week2-submit/SKILL.md', '한 번만',
                     '이미 답한 주차는 다시 묻지', '기획서 존재만으로', '지원하지 않는 주차'):
            self.assertIn(text, router)
        self.assertNotIn('python3 ', router)
        self.assertNotIn('camp_submit.py', router)

    def test_explicit_handoffs_and_separate_helpers(self):
        self.assertIn('skills/week1-submit/SKILL.md', self.skill('week1'))
        self.assertIn('skills/week2-submit/SKILL.md', self.skill('week2'))
        week1, week2 = self.skill('week1-submit'), self.skill('week2-submit')
        self.assertIn('--week 1', week1)
        self.assertNotIn('--week <1~4>', week1)
        self.assertIn('원본 포함 동의 없이', week1)
        self.assertIn('inspect', week1)
        for command in ('show', 'export', 'package'):
            self.assertIn('"<실습 폴더>" ' + command, week2)
        self.assertIn('미완료여도', week2)
        self.assertIn('prepared_locally_not_submitted', week2)
        self.assertIn('1주차 기획 ZIP으로 대체하지 않는다', week2)

if __name__ == '__main__':
    unittest.main()
