import copy
import unittest
from reconcile import fixture, reconcile

class ReconcileTests(unittest.TestCase):
    def test_partial_payment(self):
        r = reconcile(fixture())['invoices'][0]
        self.assertEqual((r['sap_open'],r['unposted_bank'],r['review_remaining'],r['overdue_days']),('600.00','300.00','300.00',6))
        self.assertEqual(r['evidence'],['T1','T2'])

    def test_repeat_import(self):
        d=fixture(); expected=reconcile(d)
        d['bank'] += copy.deepcopy(d['bank'])
        self.assertEqual(reconcile(d), expected)

    def test_conflicting_transaction(self):
        d=fixture(); r=copy.deepcopy(d['bank'][0]); r['amount']='401.00';d['bank'].append(r)
        with self.assertRaisesRegex(ValueError,'conflicting'):reconcile(d)

    def test_unknown_sap_state(self):
        d=fixture(); d['bank'][1]['sap_reflected']='unknown';r=reconcile(d)
        self.assertEqual(r['invoices'][0]['review_remaining'],'600.00')
        self.assertEqual(r['exceptions'][0]['reason'],'SAP 반영 상태 미확인')
        self.assertIn('잠정',r['invoices'][0]['status'])

    def test_unmatched_and_wrong_currency_or_dealer(self):
        for key,val in [('invoice','NO-SUCH'),('currency','USD'),('dealer','Dealer-C')]:
            with self.subTest(key=key):
                d=fixture();d['bank'][1][key]=val;r=reconcile(d)
                self.assertEqual(len(r['exceptions']),1)
                self.assertEqual(r['invoices'][0]['unposted_bank'],'0.00')

    def test_due_boundaries(self):
        for due,days in [('2026-09-06',1),('2026-09-07',0),('2026-09-08',0),('',None)]:
            with self.subTest(due=due):
                d=fixture();d['invoices'][0]['due']=due
                self.assertEqual(reconcile(d)['invoices'][0]['overdue_days'],days)

    def test_full_payment_and_overpayment(self):
        d=fixture();d['bank'][1]['amount']='600.00';r=reconcile(d)['invoices'][0]
        self.assertEqual(r['review_remaining'],'0.00');self.assertIn('전액 대응',r['status'])
        d['bank'][1]['amount']='700.00';r=reconcile(d)['invoices'][0]
        self.assertIsNone(r['review_remaining']);self.assertIn('과입금',r['status'])

    def test_invalid_snapshots_and_invoice_duplicates(self):
        d=fixture();d['invoices'][0]['as_of']='2026-09-06'
        with self.assertRaisesRegex(ValueError,'snapshot'):reconcile(d)
        d=fixture();d['invoices'].append(copy.deepcopy(d['invoices'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):reconcile(d)

    def test_reversal_and_future_receipt(self):
        for key,val in [('status','reversed'),('date','2026-09-08')]:
            d=fixture();d['bank'][1][key]=val;r=reconcile(d)
            self.assertEqual(len(r['exceptions']),1)
            self.assertEqual(r['invoices'][0]['unposted_bank'],'0.00')

    def test_invalid_money(self):
        for val in ['NaN','Infinity','-1','1.001','bad']:
            with self.subTest(value=val):
                d=fixture();d['bank'][0]['amount']=val
                with self.assertRaises(ValueError):reconcile(d)

    def test_dealer_aging(self):
        a,b=reconcile(fixture())['dealer_aging']
        self.assertEqual((a['sap_overdue'],a['review_overdue']),('600.00','300.00'))
        self.assertEqual((b['sap_overdue'],b['review_overdue']),('0.00','0.00'))

    def test_synthetic_only(self):
        d=fixture();d['synthetic']=False
        with self.assertRaisesRegex(ValueError,'합성'):reconcile(d)

if __name__ == '__main__':unittest.main()
