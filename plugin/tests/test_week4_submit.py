"""W4 CLI contract; real browser/HTTP round trip is separate."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import week4 as w
import submission_bridge as b

class Week4SubmitTests(unittest.TestCase):
    def test_production_default_uses_reviewed_bundle_and_week4_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root=str(Path(d).resolve())
            with patch.object(sys,'argv',['week4.py','submit','--root',root,'--submit']), patch.object(b,'submit',return_value={'status':'submitted'}) as submit:
                self.assertEqual(w.main(),0)
            options=submit.call_args.kwargs
            self.assertEqual(options['base'],b.PRODUCTION)
            self.assertEqual(options['scope'],4)
            self.assertIs(options['artifact_loader'],w.current_bundle)
            self.assertTrue(options['consent'])
            self.assertFalse(options['local_test'])
    def test_no_consent_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as d, patch.object(b.Client,'request') as request:
            with patch.object(sys,'argv',['week4.py','submit','--root',str(Path(d).resolve())]):
                with self.assertRaises(ValueError):w.main()
            request.assert_not_called()
    def test_ambiguous_pending_not_retried_as_new_submission(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(sys,'argv',['week4.py','submit','--root',str(Path(d).resolve()),'--submit','--no-browser','--wait','0']), patch.object(b,'submit',return_value={'status':'pending'}) as submit:
                self.assertEqual(w.main(),2)
            self.assertEqual(submit.call_count,1)
            self.assertTrue(submit.call_args.kwargs['no_browser'])
    def test_only_proven_expiry_renews_once(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(sys,'argv',['week4.py','submit','--root',str(Path(d).resolve()),'--submit']), patch.object(b,'submit',side_effect=[{'status':'expired'},{'status':'submitted'}]) as submit:
                self.assertEqual(w.main(),0)
            self.assertEqual(submit.call_count,2)

if __name__=='__main__':unittest.main()
