"""Synthetic client recovery regression; not production or OAuth evidence."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_submission_bridge import fixture
import submission_bridge as b

class Recovery(unittest.TestCase):
    def test_rejected_saved_connection_can_reconnect_without_manual_file_edits(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'HOME': str(Path(tmp).resolve())}):
            root=Path(tmp).resolve()/'case'; fixture(root)
            base='http://127.0.0.1:12345'; path=b.config_directory(base)/'device.json'
            b.private_write(path, {'token':'x'*43, 'expires_at':'2099-01-01T00:00:00Z'})
            tokens=[]
            def request(client, action, payload, token=None, content_type='application/json'):
                if action=='prepare':
                    tokens.append(token)
                    if token:
                        error=getattr(b,'AuthenticationRequired',ValueError)
                        raise error('제출 API 거절 (HTTP 403)')
                    return {'id':'synthetic-recovery','upload_token':'u'*43,'approval_url':base+'/?view=learning#submit-report=synthetic-recovery:'+'a'*43,'expires_at':'2099-01-01T00:00:00Z'}
                if action=='status':return {'id':'synthetic-recovery','status':'pending_authorization'}
                raise AssertionError(action)
            with patch.object(b.Client,'request',request), patch.object(b.webbrowser,'open',return_value=True) as browser:
                result=b.submit(root,consent=True,base=base,local_test=True,wait=0)
            self.assertEqual(result['status'],'pending')
            self.assertEqual(tokens,['x'*43,None])
            self.assertEqual(browser.call_count,1)
            self.assertFalse(path.exists())
if __name__=='__main__':unittest.main()
