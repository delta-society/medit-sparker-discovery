"""Static curriculum wiring, not model dialogue acceptance."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LessonContractTests(unittest.TestCase):
    def test_sequence_and_learner_boundaries(self):
        text = (ROOT/'skills/week2/SKILL.md').read_text()
        headings = ['## 1. 제품을 먼저', '## 2. 방금 만든', '## 3. 실습①',
                    '## 4. 실습②', '## 5. 기초지식', '## 6. 실습④', '## 7. 시연']
        self.assertEqual(sorted(text.index(h) for h in headings), [text.index(h) for h in headings])
        for required in ['같은 입력으로 변경 전후', '바꿀 것·유지할 것·변경 후 예상 결과',
                         '재실행', '강의 대기', '실제 절대 경로', '원본 기획과 과거 리비전',
                         '개발 중 AI와 실행 중 AI', '제출을 명시 요청한 경우에만',
                         '브라우저 도구가 없으면', '범위 확정 발화를 만들지', 'week2-lesson.md']:
            self.assertIn(required, text)

    def test_release_includes_lesson(self):
        import importlib.util
        s = importlib.util.spec_from_file_location('lesson_build', ROOT.parent/'scripts/build-package.py')
        assert s is not None and s.loader is not None
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        self.assertIn('references/week2-lesson.md', m.PLUGIN_FILES)
        for name in m.PLUGIN_FILES:
            self.assertTrue((ROOT/name).is_file(), name)

if __name__ == '__main__': unittest.main()
