"""Local synthetic proxy privacy regressions; no provider or model requests."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import threading
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    'qa_egress_proxy', Path(__file__).resolve().parents[1] / 'qa/egress_proxy.py')
proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proxy)


class ProxyPrivacyTests(unittest.TestCase):
    def test_denied_connect_never_logs_target_or_resolves_it(self):
        secret = 'SYNTHETIC-OAUTH-SECRET'
        targets = [secret + '.example.invalid:443',
                   'api.anthropic.com:' + secret,
                   secret + '@api.anthropic.com:443']
        server = proxy.Server(('127.0.0.1', 0), proxy.Handler)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), \
             patch.object(proxy.socket, 'getaddrinfo', side_effect=AssertionError('denied destination resolved')) as resolver:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for target in targets:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                        client.settimeout(5)
                        client.connect(server.server_address)
                        client.sendall(('CONNECT ' + target + ' HTTP/1.1\r\nHost: unused\r\n\r\n').encode('ascii'))
                        response = client.recv(4096)
                        self.assertIn(b' 403 ', response.split(b'\r\n', 1)[0])
                resolver.assert_not_called()
            finally:
                server.shutdown()
                worker.join(5)
                server.server_close()
        self.assertFalse(worker.is_alive())
        log = output.getvalue()
        self.assertNotIn(secret, log)
        events = [json.loads(line) for line in log.splitlines()]
        self.assertEqual(len(events), len(targets))
        self.assertTrue(all(e['host'] == '[denied]' and e['allowed'] is False for e in events))


if __name__ == '__main__':
    unittest.main()
