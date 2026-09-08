"""Disposable Linux QA bootstrap: set namespace egress rules, then drop caps.

The sole credential arrives on stdin and is never written to a file or printed.
Only /src (read-only code) and /qa (synthetic run artifacts) are mounted.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

settings = json.load(sys.stdin)
proxy_ip = os.environ['QA_PROXY_IP']
subprocess.run(['iptables', '-P', 'OUTPUT', 'DROP'], check=True)
for rule in [
    ['-p', 'udp', '--dport', '53', '-j', 'DROP'],
    ['-p', 'tcp', '--dport', '53', '-j', 'DROP'],
    ['-d', proxy_ip, '-p', 'tcp', '--dport', '3128', '-j', 'ACCEPT'],
    ['-o', 'lo', '-j', 'ACCEPT'],
]:
    subprocess.run(['iptables', '-A', 'OUTPUT', *rule], check=True)
subprocess.run(['ip6tables', '-P', 'OUTPUT', 'DROP'], check=True)
os.environ.update(CLAUDE_CODE_OAUTH_TOKEN=settings['oauth_token'],
                  HTTPS_PROXY=f'http://{proxy_ip}:3128',
                  CLAUDE_CODE_PROXY_RESOLVES_HOSTS='1')
command = ['python3', '/src/scripts/qa_claude.py', *settings['args']]
os.execvp('setpriv', ['setpriv', '--reuid=1000', '--regid=1000', '--clear-groups',
                     '--bounding-set=-all', '--inh-caps=-all', '--ambient-caps=-all',
                     '--no-new-privs', *command])
