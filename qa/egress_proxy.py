"""QA-only CONNECT proxy. Logs destination decisions, never TLS payloads/auth.

Run on a private container network. The QA container has no direct egress and
can only connect to this proxy's port. This is not an authentication proxy.
"""
import http.server
import ipaddress
import json
import select
import socket
import socketserver
import time

ALLOWED = {'api.anthropic.com', 'claude.ai'}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_CONNECT(self):
        host, _, port = self.path.rpartition(':')
        allowed = host in ALLOWED and port == '443'
        print(json.dumps(dict(time=time.time(), host=host if allowed else '[denied]', allowed=allowed)), flush=True)
        if not allowed:
            self.send_error(403)
            return
        target = None
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            for family, kind, proto, _, address in addresses:
                if not ipaddress.ip_address(address[0]).is_global:
                    continue
                try:
                    target = socket.socket(family, kind, proto)
                    target.settimeout(15)
                    target.connect(address)
                    break
                except OSError:
                    target.close()
                    target = None
            if target is None:
                self.send_error(502)
                return
            self.send_response(200, 'Connection established')
            self.end_headers()
            self.wfile.flush()
            sockets = [self.connection, target]
            while True:
                ready, _, _ = select.select(sockets, [], [], 120)
                if not ready:
                    break
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    (target if source is self.connection else self.connection).sendall(data)
        except OSError:
            pass
        finally:
            if target:
                target.close()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    Server(('0.0.0.0', 3128), Handler).serve_forever()
