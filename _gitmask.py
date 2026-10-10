# -*- coding: utf-8 -*-
"""只读：脱敏显示公开分支里的 key 命中。不写任何东西。"""
import subprocess, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = r'D:\7tan\7tanAI'

def git(*a):
    r = subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout or ''

PAT = re.compile(r'(ark-[0-9a-fA-F\-]{16,}|sk-[A-Za-z0-9]{16,}|AIza[A-Za-z0-9\-_]{20,})')

def mask(s):
    def f(m):
        t = m.group(0)
        return t[:6] + '***' + t[-4:]
    return PAT.sub(f, s)

for ref, path in [('origin/develop', 'config/config.yaml'),
                  ('origin/develop', 'src/ui/welcome_wizard.py'),
                  ('origin/main', 'src/ui/welcome_wizard.py')]:
    out = git('grep', '-n', '-I', '-E', 'ark-[0-9a-fA-F-]{16,}|sk-[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_-]{20,}', ref, '--', path)
    print('### %s : %s' % (ref, path))
    for line in out.splitlines():
        print('   ', mask(line)[:200])
    if not out.strip():
        print('    (无)')
    print()

print('### 待推送提交里新增的 key 文件（本地 develop）')
out = git('grep', '-n', '-I', '--', 'develop', '--', '*gen_shot24_fix.py')
for line in out.splitlines():
    print('   ', mask(line)[:180])
