# -*- coding: utf-8 -*-
"""只读：扫描「即将推送到公开仓库」的内容里有没有凭据。不写任何东西。"""
import subprocess, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = r'D:\7tan\7tanAI'

def git(*a):
    r = subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout or ''

PAT = re.compile(r'(?i)(123466|password\s*[:=]\s*["\']?[^\s"\']{4,}|passwd\s*[:=]|'
                 r'api[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9\-_]{12,}|'
                 r'sk-[A-Za-z0-9]{16,}|ark-[0-9a-fA-F\-]{16,}|'
                 r'BEGIN [A-Z ]*PRIVATE KEY|sshpass|Bearer\s+[A-Za-z0-9\-_.]{20,})')

def scan_patch(label, args):
    patch = git(*args)
    print('=== %s ===' % label)
    print('  patch 大小 = %.2f MB' % (len(patch.encode('utf-8', 'replace')) / 1048576.0))
    cur = '(未知)'
    hits = []
    for line in patch.splitlines():
        if line.startswith('diff --git '):
            cur = line.split(' b/')[-1]
        elif line.startswith('+') and not line.startswith('+++'):
            if PAT.search(line):
                hits.append((cur, line[1:].strip()[:130]))
    print('  命中 =', len(hits))
    seen = {}
    for f, l in hits:
        seen.setdefault(f, []).append(l)
    for f, ls in list(seen.items())[:40]:
        print('  [%d] %s' % (len(ls), f))
        for l in ls[:3]:
            print('        %s' % l)
    print()

scan_patch('待推送提交 origin/develop..develop', ['diff', 'origin/develop', 'develop'])
scan_patch('工作区未提交改动 HEAD..工作区', ['diff', 'HEAD'])

print('=== HEAD 已跟踪文件里搜已知口令 123466 ===')
r = git('grep', '-n', '-I', '123466', 'HEAD')
print(r.strip()[:2000] or '  （无命中）')
