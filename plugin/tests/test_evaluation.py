import copy, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import evaluation as e

class EvaluationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()/'case';self.d=e.template()
 def tearDown(self):self.tmp.cleanup()
 def test_draft_resume(self):
  r=e.save(self.root,self.d);self.assertEqual(e.load(self.root),r)
 def test_confirm_requires_review(self):
  r=e.save(self.root,self.d)
  with self.assertRaises(ValueError):e.save(self.root,self.d,'합성 확인',r['digest'])
 def test_unknown_can_finish_and_edit_resets(self):
  for x in self.d['criteria']:x['reviewed']=True
  r=e.save(self.root,self.d);r=e.save(self.root,self.d,'합성 시험 확인',r['digest']);self.assertEqual(r['status'],'confirmed')
  self.d['purpose']='변경';r=e.save(self.root,self.d);self.assertEqual(r['status'],'draft');self.assertEqual(e.load(self.root),r)
 def test_stale_confirmation(self):
  for x in self.d['criteria']:x['reviewed']=True
  r=e.save(self.root,self.d);self.d['purpose']='변경';e.save(self.root,self.d)
  with self.assertRaises(ValueError):e.save(self.root,self.d,'확인',r['digest'])
 def test_no_silent_truncation(self):
  self.d['criteria'][0]['basis']='가'*161
  with self.assertRaises(ValueError):e.validate(self.d)
 def test_no_unknown_promoted(self):
  self.d['criteria'][0]['judgment']='확인됨'
  with self.assertRaises(ValueError):e.validate(self.d)
 def test_secrets_rejected(self):
  self.d['purpose']='password: synthetic-test-only'
  with self.assertRaises(ValueError):e.validate(self.d)
 def test_html_escaped(self):
  self.d['title']='<script>alert(1)</script>'
  r=e.save(self.root,self.d);self.assertIn('&lt;script&gt;',e.document(r));self.assertNotIn('<script>alert(1)',e.document(r))
 def test_tamper_rejected(self):
  e.save(self.root,self.d);p=self.root/'r000001.json';r=json.loads(p.read_text());r['document']['title']='tampered';p.write_text(json.dumps(r))
  with self.assertRaises(ValueError):e.load(self.root)
 def test_draft_pdf_rejected(self):
  r=e.save(self.root,self.d)
  with self.assertRaises(ValueError):e.export(self.root,r)
 def test_six_exact_names(self):
  self.d['criteria'][1]['name']='쓸 이유'
  with self.assertRaises(ValueError):e.validate(self.d)
if __name__=='__main__':unittest.main()
