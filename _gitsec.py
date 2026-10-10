# -*- coding: utf-8 -*-
"""只读扫描：将要被提交的文件里有没有凭据/大文件。不写任何东西。"""
import subprocess, os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = r'D:\7tan\7tanAI'

def git(*a):
    r = subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout

untracked = [l for l in git('ls-files', '--others', '--exclude-standard').splitlines() if l.strip()]
changed   = [l for l in git('diff', '--name-only').splitlines() if l.strip()]
staged    = [l for l in git('diff', '--cached', '--name-only').splitlines() if l.strip()]
tracked   = [l for l in git('ls-files').splitlines() if l.strip()]

cands = []
for p in sorted(set(untracked + changed + staged)):
    fp = os.path.join(REPO, p)
    if os.path.isfile(fp):
        cands.append((p, fp))

print('=== 计数 ===')
print('未跟踪(未忽略) =', len(untracked))
print('已跟踪但改动   =', len(changed))
print('已暂存         =', len(staged))
print('候选(存在的文件) =', len(cands))
print('全库已跟踪文件 =', len(tracked))

PAT = re.compile(r'(?i)(password|passwd|pwd\s*=|api[_-]?key|apikey|secret|access[_-]?token|auth[_-]?token|bearer\s+[A-Za-z0-9]|sk-[A-Za-z0-9]{10,}|ark-[0-9a-fA-F-]{16,}|private[_-]?key|BEGIN [A-Z ]*PRIVATE KEY|sshpass|root@|服务器密码)')
TEXT_EXT = {'.py', '.json', '.txt', '.md', '.bat', '.ps1', '.cmd', '.css', '.js',
            '.html', '.htm', '.yaml', '.yml', '.ini', '.cfg', '.env', '.sh',
            '.vbs', '.xml', '.sql', '.csv', '.log', '.spec', '.example'}

hits = []
scanned = 0
for p, fp in cands:
    ext = os.path.splitext(p)[1].lower()
    if ext not in TEXT_EXT:
        continue
    scanned += 1
    try:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f, 1):
                if PAT.search(line):
                    hits.append((p, i, line.strip()[:150]))
    except Exception:
        pass

print('\n=== 文本文件扫描 ===')
print('扫描文件数 =', scanned, ' 命中 =', len(hits))
for p, i, l in hits[:120]:
    print('  %s:%d: %s' % (p, i, l))

print('\n=== 大文件 (>2MB，会被提交的) ===')
big = [(p, os.path.getsize(fp)) for p, fp in cands if os.path.getsize(fp) > 2 * 1024 * 1024]
big.sort(key=lambda x: -x[1])
if not big:
    print('  无')
for p, s in big[:40]:
    print('  %8.2f MB  %s' % (s / 1048576.0, p))

print('\n=== 候选按扩展名分布 ===')
from collections import Counter
c = Counter(os.path.splitext(p)[1].lower() or '(无)' for p, _ in cands)
for k, v in c.most_common():
    print('  %-8s %d' % (k, v))
