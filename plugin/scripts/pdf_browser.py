"""Local Chrome/Edge PDF transport using Python stdlib and the DevTools protocol.

Never attaches to a user's browser profile. No driver, Node, server, or downloads.
"""
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit


class PdfError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def browser_candidates(environ=None, platform=None):
    env = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    override = env.get('SPARKER_PDF_BROWSER')
    if override:
        path = Path(override).expanduser()
        return [path] if path.is_absolute() else []
    paths = []
    if platform == 'win32':
        for variable in ['PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA']:
            root = env.get(variable)
            if root:
                for relative in ['Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe']:
                    paths.append(Path(root) / relative)
    elif platform == 'darwin':
        for root in [Path('/Applications'), Path.home() / 'Applications']:
            for name in ['Google Chrome', 'Microsoft Edge']:
                paths.append(root / f'{name}.app/Contents/MacOS/{name}')
    else:
        for name in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge']:
            found = shutil.which(name)
            if found:
                paths.append(Path(found))
    return paths


def find_browser():
    for path in browser_candidates():
        if path.is_file():
            return path
    raise PdfError('browser_missing', 'PDF를 만들 Edge 또는 Chrome을 찾지 못했습니다. 기획서는 안전하게 저장되어 있습니다.')


class DevTools:
    """Small synchronous RFC6455 client for our own loopback DevTools endpoint."""
    MAX_MESSAGE = 64 * 1024 * 1024

    def __init__(self, url, port, deadline):
        parsed = urlsplit(url)
        if parsed.scheme != 'ws' or parsed.hostname != '127.0.0.1' or parsed.port != port:
            raise PdfError('browser_protocol', '로컬 브라우저 연결 주소가 올바르지 않습니다.')
        self.deadline = deadline
        self.sequence = 0
        self.sock = socket.create_connection(('127.0.0.1', port), timeout=5)
        key = base64.b64encode(secrets.token_bytes(16)).decode('ascii')
        request = (f'GET {parsed.path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
                   f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                   'Sec-WebSocket-Version: 13\r\n\r\n')
        try:
            self.sock.sendall(request.encode('ascii'))
            response = b''
            while not response.endswith(b'\r\n\r\n'):
                if len(response) > 16384:
                    raise PdfError('browser_protocol', '브라우저 연결 응답이 너무 큽니다.')
                response += self._read(1)
            lines = response.decode('ascii').split('\r\n')
            headers = {line.split(':', 1)[0].lower(): line.split(':', 1)[1].strip()
                       for line in lines[1:] if ':' in line}
            expected = base64.b64encode(hashlib.sha1(
                (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode('ascii')).digest()).decode('ascii')
            if not lines[0].startswith('HTTP/1.1 101 ') or headers.get('sec-websocket-accept') != expected:
                raise PdfError('browser_protocol', '브라우저 연결을 확인하지 못했습니다.')
        except BaseException:
            self.close()
            raise

    def close(self):
        self.sock.close()

    def _read(self, size):
        parts = []
        while size:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('PDF deadline')
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(min(size, 65536))
            if not chunk:
                raise PdfError('browser_closed', 'PDF를 만드는 중 브라우저 연결이 종료되었습니다.')
            parts.append(chunk)
            size -= len(chunk)
        return b''.join(parts)

    def _send(self, payload, opcode=1):
        length = len(payload)
        header = bytes([0x80 | opcode])
        if length < 126:
            header += bytes([0x80 | length])
        elif length <= 65535:
            header += b'\xfe' + struct.pack('!H', length)
        else:
            header += b'\xff' + struct.pack('!Q', length)
        mask = secrets.token_bytes(4)
        masked = bytearray(payload)
        for i, byte in enumerate(masked):
            masked[i] = byte ^ mask[i % 4]
        self.sock.sendall(header + mask + masked)

    def _receive(self):
        chunks = []
        total = 0
        while True:
            first, second = self._read(2)
            if first & 0x70 or second & 0x80:
                raise PdfError('browser_protocol', '지원하지 않는 브라우저 프레임입니다.')
            opcode, final = first & 15, bool(first & 128)
            length = second & 127
            if length == 126:
                length = struct.unpack('!H', self._read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self._read(8))[0]
            if length + total > self.MAX_MESSAGE:
                raise PdfError('pdf_too_large', 'PDF 출력 크기가 한도를 넘었습니다.')
            payload = self._read(length)
            if opcode == 8:
                raise PdfError('browser_closed', '브라우저 연결이 종료되었습니다.')
            if opcode == 9:
                self._send(payload, 10)
                continue
            if opcode == 10:
                continue
            if opcode not in [0, 1]:
                raise PdfError('browser_protocol', '지원하지 않는 브라우저 메시지입니다.')
            chunks.append(payload)
            total += length
            if final:
                return json.loads(b''.join(chunks).decode('utf-8'))

    def call(self, method, params=None):
        self.sequence += 1
        self._send(json.dumps({'id': self.sequence, 'method': method, 'params': params or {}},
                              ensure_ascii=True, separators=(',', ':')).encode('utf-8'))
        while True:
            message = self._receive()
            if message.get('id') == self.sequence:
                if 'error' in message:
                    raise PdfError('browser_protocol', '브라우저가 PDF 처리 요청을 완료하지 못했습니다.')
                return message.get('result', {})



def wait_for_page(port, process, deadline):
    """DevTools can listen before Chrome has created its initial about:blank tab."""
    while True:
        if process.poll() is not None:
            raise PdfError('browser_launch', '브라우저를 PDF 출력용으로 실행하지 못했습니다.')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('browser page startup')
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=min(5, remaining))
        try:
            connection.request('GET', '/json/list')
            response = connection.getresponse()
            if response.status != 200:
                raise PdfError('browser_protocol', '브라우저 페이지를 찾지 못했습니다.')
            targets = json.loads(response.read(65536))
        finally:
            connection.close()
        target = next((item for item in targets if item.get('type') == 'page' and item.get('url') == 'about:blank'), None)
        if target is not None:
            return target
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))


def print_pdf(html, footer, browser=None, timeout=90):
    """Return validated PDF bytes and renderer observations. No output publication."""
    executable = Path(browser) if browser else find_browser()
    deadline = time.monotonic() + timeout
    profile = tempfile.mkdtemp(prefix='sparker-pdf-')
    process = client = None
    try:
        args = [str(executable), '--headless', '--remote-debugging-address=127.0.0.1',
                '--remote-debugging-port=0', f'--user-data-dir={profile}',
                '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
                '--disable-component-update', '--disable-sync', '--disable-extensions',
                '--disable-default-apps', '--metrics-recording-only', '--password-store=basic',
                '--disable-features=Translate', 'about:blank']
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        portfile = Path(profile) / 'DevToolsActivePort'
        while not portfile.exists() or not portfile.read_text(encoding="utf-8").strip():
            if process.poll() is not None:
                raise PdfError('browser_launch', '브라우저를 PDF 출력용으로 실행하지 못했습니다.')
            if time.monotonic() > min(deadline, deadline - timeout + 15):
                raise TimeoutError('browser startup')
            time.sleep(0.05)
        lines = portfile.read_text(encoding='utf-8').splitlines()
        port = int(lines[0])
        target = wait_for_page(port, process, min(deadline, time.monotonic() + 10))
        client = DevTools(target['webSocketDebuggerUrl'], port, deadline)
        version = client.call('Browser.getVersion')['product']
        client.call('Page.enable')
        client.call('Network.enable')
        client.call('Network.setBlockedURLs', {'urls': ['http://*', 'https://*', 'file://*', 'ftp://*']})
        client.call('Emulation.setDeviceMetricsOverride', {'width': 794, 'height': 1123,
                                                          'deviceScaleFactor': 1, 'mobile': False})
        client.call('Emulation.setEmulatedMedia', {'media': 'print', 'features': [
            {'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        frame = client.call('Page.getFrameTree')['frameTree']['frame']['id']
        client.call('Page.setDocumentContent', {'frameId': frame, 'html': html})
        ready = client.call('Runtime.evaluate', {
            'expression': 'window.__sparkerPdfReady', 'awaitPromise': True, 'returnByValue': True})
        observation = ready.get('result', {}).get('value', {})
        if not isinstance(observation, dict) or not observation.get('ok'):
            code = observation.get('code', 'render') if isinstance(observation, dict) else 'render'
            messages = {'diagram': '업무 도식을 그리지 못했습니다. 기획서는 보존되며 도식 내용을 확인한 뒤 PDF만 다시 만들 수 있습니다.',
                        'diagram_too_large': '도식이 A4에 읽기 좋은 크기로 들어가지 않습니다. 도식을 나누어 다시 출력해야 합니다.',
                        'font': '번들 한글 글꼴을 불러오지 못했습니다.',
                        'layout': 'A4 너비를 벗어난 내용이 있어 PDF 생성을 보류했습니다.'}
            raise PdfError(code, messages.get(code, '문서 렌더링이 완료되지 않아 PDF를 저장하지 않았습니다.'))
        result = client.call('Page.printToPDF', {
            'printBackground': True, 'preferCSSPageSize': True,
            'paperWidth': 210 / 25.4, 'paperHeight': 297 / 25.4,
            'displayHeaderFooter': True, 'headerTemplate': '<span></span>', 'footerTemplate': footer,
        })
        pdf = base64.b64decode(result['data'], validate=True)
        if not pdf.startswith(b'%PDF-') or b'%%EOF' not in pdf[-1024:]:
            raise PdfError('invalid_pdf', '완전한 PDF 출력인지 확인하지 못했습니다.')
        return pdf, {**observation, 'browser': version}
    except PdfError:
        raise
    except (TimeoutError, socket.timeout) as exc:
        raise PdfError('timeout', 'PDF 생성 시간이 초과되었습니다. 확정된 기획서는 보존되어 있습니다.') from exc
    except (OSError, ValueError, KeyError, IndexError, StopIteration, http.client.HTTPException) as exc:
        raise PdfError('browser_failed', '로컬 브라우저의 PDF 출력을 완료하지 못했습니다. 기획서는 보존되어 있습니다.') from exc
    finally:
        if client:
            try:
                client.deadline = time.monotonic() + 3
                client.call('Browser.close')
            except (OSError, ValueError):
                pass
            client.close()
        if process is not None:
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        # Browser children can briefly retain locks on Windows. Never touch the user's profile.
        for attempt in range(5):
            try:
                shutil.rmtree(profile)
                break
            except OSError:
                time.sleep(0.1 * (attempt + 1))
