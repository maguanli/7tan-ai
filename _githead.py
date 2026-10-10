# -*- coding: utf-8 -*-
"""只读：检查远程已有树 / 本地 HEAD 里有没有硬编码 key。不写任何东西。"""
import subprocess, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = r'D:\7tan\7tanAI'

def git(*a):
    r = subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout or ''

REFS = ['origin/develop', 'origin/main', 'origin/source', 'develop', 'master']
PAT = re.compile(r'(ark-[0-9a-fA-F\-]{16,}|sk-[A-Za-z0-9]{16,}|AIza[A-Za-z0-9\-_]{20,})')

for ref in REFS:
    ok = git('rev-parse', '--verify', '--quiet', ref).strip()
    if not ok:
        print('%-16s (不存在)' % ref)
        continue
    out = git('grep', '-n', '-I', '-E', 'ark-[0-9a-fA-F-]{16,}|sk-[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_-]{20,}', ref)
    files = {}
    for line in out.splitlines():
        partes = line.split(':', 2)
        if len(partes) >= 2:
            files.setdefault(partes[1] if False else line.split(':')[1], []).append(line)
    # 上面取法在含 ':' 的 ref 下不稳，改为直接按 ref: 前缀剥离
    files = {}
    for line in out.splitlines():
        rest = line[len(ref) + 1:] if line.startswith(ref + ':') else line
        p = rest.split(':', 1)[0]
        files.setdefault(p, 0)
        files[p] += 1
    print('%-16s 命中行数=%d  文件数=%d' % (ref, len(out.splitlines()), len(files)))
    for f, c in list(files.items())[:25]:
        print('        [%d] %s' % (c, f))
print()
print('=== 差异：develop 有、origin/develop 没有的 key 文件 ===')
d = set()
for line in git('grep', '-l', '-I', '-E', 'ark-[0-9a-fA-F-]{16,}|sk-[A-Za-z0-9]{16,}', 'develop').splitlines():
    d.add(line.split(':', 1)[-1] if ':' in line else line)
o = set()
for line in git('grep', '-l', '-I', '-E', 'ark-[0-9a-fA-F-]{16,}|sk-[A-Za-z0-9]{16,}', 'origin/develop').splitlines():
    o.add(line.split(':', 1)[-1] if ':' in line else line)
new = sorted(x for x in d if x not in o)
print('本地新增含 key 文件数 =', len(new))
for x in new[:40]:
    print('   +', x)
