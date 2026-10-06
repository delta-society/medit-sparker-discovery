"""Synthetic fixtures for catch-up validation; HTTP integration is separate."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import catchup_submit as c
import camp_submit as camp
import implementation as impl
from plan import Store, template
from test_submission_bridge import fixture


def fixtures(base):
    project = base / '한글 과제'; project.mkdir(parents=True)
    root = project / '.sparker-discovery'
    Store(root).write('example-case', 'new', plan=template(linked=True))
    one = project / 'week1.zip'
    camp.prepare(root, 'example-case', 1, 1, project, [], one)
    # Synthetic package in the actual generator's exact format; not real learner evidence.
    files = {'app.py': b'print("SYNTHETIC")\n', 'README.md': b'SYNTHETIC: python app.py',
             'implementation.md': b'# SYNTHETIC package fixture, not actual participant work'}
    manifest = dict(format='sparker-week2-local-v1', state='prepared_locally_not_submitted',
                    week=2, record_sha256='a'*64, files={n:camp.sha(d) for n,d in files.items()})
    files['manifest.json'] = json.dumps(manifest).encode()
    two = project / 'week2.zip'
    with zipfile.ZipFile(two, 'w') as z:
        for name, data in files.items(): z.writestr(name, data)
    three = project / '.sparker-evaluation' / 'synthetic'; fixture(three)
    return [dict(week=i, path=str(p)) for i,p in enumerate([one,two,three],1)]


class CatchupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.items = fixtures(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def pinned(self):
        return [{k: r[k] for k in ('week', 'path', 'sha256')} for r in c.inspect_items(self.items)]

    def test_each_week_uses_its_actual_artifact(self):
        rows = c.inspect_items(list(reversed(self.items)))
        self.assertEqual([r['week'] for r in rows], [1,2,3])
        self.assertEqual([r['filename'] for r in rows], list(c.NAMES.values()))
        self.assertTrue(all(r['status'] == 'ready' for r in rows))
        self.assertEqual(camp.inspect(self.items[0]['path'])['manifest']['plan']['status'], 'draft')

    def test_wrong_week_zip_is_not_renamed_into_valid_submission(self):
        for w,p in [(2,self.items[0]['path']), (1,self.items[1]['path'])]:
            self.assertEqual(c.inspect_items([dict(week=w,path=p)])[0]['status'], 'blocked')

    def test_missing_one_does_not_block_others(self):
        Path(self.items[1]['path']).unlink()
        self.assertEqual([r['status'] for r in c.inspect_items(self.items)], ['ready','blocked','ready'])

    def test_duplicate_week_and_unsupported_week_rejected(self):
        for rows in [[self.items[0], self.items[0]], [dict(week=4,path=self.items[0]['path'])], [dict(week=True,path=self.items[0]['path'])]]:
            with self.assertRaises(ValueError): c.inspect_items(rows)

    def test_sha_change_blocks_only_changed_item_before_network(self):
        rows = self.pinned()
        rows[1]['sha256'] = '0'*64
        with patch.object(c.bridge,'submit',return_value={'status':'submitted'}) as submit:
            result = c.submit_items(rows,consent=True)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual([r['status'] for r in result['items']], ['submitted','blocked','submitted'])
        self.assertEqual([call.kwargs['scope'] for call in submit.call_args_list], [1,3])

    def test_no_consent_or_unpinned_list_never_transmits(self):
        with patch.object(c.bridge,'submit') as submit:
            with self.assertRaises(ValueError): c.submit_items(self.pinned())
            with self.assertRaises(ValueError): c.submit_items(self.items,consent=True)
        submit.assert_not_called()

    def test_failed_week_and_pending_week_remain_independent(self):
        with patch.object(c.bridge,'submit',side_effect=[{'status':'submitted'},ValueError('blocked'),{'status':'pending','resumable':True}]):
            result=c.submit_items(self.pinned(),consent=True)
        self.assertEqual([r['status'] for r in result['items']], ['submitted','blocked','pending'])

    def test_cli_inspect_and_package_builder_include_catchup(self):
        source=Path(__file__).resolve().parents[2]
        items=self.root/'items.json';items.write_text(json.dumps(self.items))
        r=subprocess.run([sys.executable,str(source/'plugin/scripts/catchup_submit.py'),'inspect','--items',str(items)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['status'],'inspected_not_submitted')
        output=self.root/'release.zip'
        r=subprocess.run([sys.executable,str(source/'scripts/build-package.py'),'--output',str(output)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        with zipfile.ZipFile(output) as z:
            for f in ['scripts/catchup_submit.py','skills/catchup-submit/SKILL.md']:
                self.assertEqual(z.read(f),(source/'plugin'/f).read_bytes())
            z.extractall(self.root/'plugin')
        r=subprocess.run([sys.executable,str(self.root/'plugin/scripts/catchup_submit.py'),'inspect','--items',str(items)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue(all(x['status']=='ready' for x in json.loads(r.stdout)['items']))

    def test_manifest_payload_tamper_blocked(self):
        path=Path(self.items[1]['path'])
        with zipfile.ZipFile(path) as z: data={n:z.read(n) for n in z.namelist()}
        data['app.py']=b'print("CHANGED")'
        with zipfile.ZipFile(path,'w') as z:
            for n,d in data.items():z.writestr(n,d)
        self.assertEqual(c.inspect_items([self.items[1]])[0]['status'],'blocked')


if __name__=='__main__':unittest.main()
