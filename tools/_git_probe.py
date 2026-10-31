# -*- coding: utf-8 -*-
"""测试 git push 认证（dry-run），不真正推送。"""
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def g(*args, timeout=90):
    p = subprocess.run(['git'] + list(args), cwd=r'D:\7tan\7tanAI',
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or '')

rc, out = g('remote', '-v')
print('== remotes ==')
print(out)

rc, out = g('config', '--get', 'credential.helper')
print('== credential.helper ==', rc, repr(out.strip()))

rc, out = g('rev-parse', '--abbrev-ref', 'HEAD')
print('== branch ==', out.strip())

print('== push --dry-run ==')
rc, out = g('push', '--dry-run', 'origin', 'HEAD', timeout=120)
print('rc =', rc)
print(out[:2000])
