import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from example import ar_example, st_example

class ExampleTests(unittest.TestCase):
    def case(self, **kw):
        d=dict(sap_open='600',receipt='300',posted='unknown',aligned='unknown',due='2026-09-01',as_of='2026-09-07',currency='EUR')
        d.update(kw)
        return ar_example(**d)

    def test_mixed_question_formats(self):
        closed=self.case()['markdown'].split('**질문 하나:** ')[1]
        for label in ['① 이미 반영','② 아직 미반영','기타: 직접 입력','아직 모름','자기 말']:
            self.assertIn(label,closed)
        opened=self.case(posted='yes',aligned='unknown')['markdown'].split('**질문 하나:** ')[1]
        self.assertIn('어떤 조회나 자료',opened)
        self.assertNotIn('①',opened)

    def test_unknown_no_numeric_collection_action(self):
        r=self.case()
        self.assertIsNone(r['review_balance'])
        self.assertEqual(r['next_action'],'SAP 반영상태와 기준시점 정합성을 확인한다. 잔액 수정·회수 금액은 아직 정하지 않는다.')
        self.assertNotIn('잔여 300',r['markdown'])

    def test_posted_preserves_sap_balance(self):
        r=self.case(posted='yes',aligned='yes')
        self.assertEqual(r['review_balance'],'600.00')
        self.assertIn('600.00 EUR',r['next_action'])
        self.assertIn('다시 차감하지 않는다',r['next_action'])

    def test_unposted_subtracts_once(self):
        r=self.case(posted='no',aligned='yes')
        self.assertEqual(r['review_balance'],'300.00')
        self.assertIn('300.00 EUR',r['next_action'])

    def test_alignment_unknown_even_posted_does_not_release(self):
        for posted in ['yes','no']:
            with self.subTest(posted=posted):
                self.assertIsNone(self.case(posted=posted)['review_balance'])

    def test_misalignment_does_not_release(self):
        self.assertIsNone(self.case(posted='yes',aligned='no')['review_balance'])

    def test_overpayment_not_negative_receivable(self):
        r=self.case(receipt='700',posted='no',aligned='yes')
        self.assertIsNone(r['review_balance'])
        self.assertIn('초과',r['next_action'])

    def test_dates_no_invented_bucket(self):
        r=self.case()
        self.assertEqual(r['aging_days'],6)
        self.assertNotIn('0–30',r['markdown'])
        self.assertNotIn('정상',r['markdown'])
        self.assertEqual(self.case(due='2026-09-07')['aging_days'],0)
        self.assertEqual(self.case(due='2026-10-01')['aging_days'],0)

    def test_missing_dates_keeps_aging_unknown(self):
        r=self.case(due=None)
        self.assertIsNone(r['aging_days'])
        self.assertIn('지급기일 또는 기준일 미확인',r['markdown'])

    def test_invalid_inputs_rejected(self):
        for kw in [dict(sap_open='NaN'),dict(receipt='-1'),dict(receipt='1.001'),dict(receipt='1e5'),dict(posted='maybe'),dict(aligned='true'),dict(due='2026-02-30'),dict(currency='EUR|USD')]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.case(**kw)

    def test_no_partial_or_receipt_date_invention(self):
        r=self.case()
        self.assertNotIn('분할 여부',r['markdown'])
        self.assertNotIn('입금일',r['markdown'])

class STExampleTests(unittest.TestCase):
    def test_unknown_formula_not_invented(self):
        r=st_example('10','20','3')
        self.assertEqual(r['processing_minutes'],'30.00')
        self.assertIsNone(r['st_value'])
        self.assertNotIn('1 +',r['markdown'])
        self.assertIn('산식을 제시하지 않음',r['markdown'])
    def test_bad_quantity_rejected(self):
        for q in ['0','-1','1.5','NaN']:
            with self.assertRaises(ValueError):st_example(q,'20','3')

if __name__ == '__main__':unittest.main()
