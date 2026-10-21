# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
print('CWD:', os.getcwd())
print()
hits = []
for base in [os.getcwd(), r'D:\用户目录\下载']:
    if not os.path.isdir(base):
        continue
    for dp, dn, fn in os.walk(base):
        parts = dp.split(os.sep)
        if any(p in ('.git', 'node_modules', '__pycache__', 'venv', '.venv', 'site-packages') for p in parts):
            dn[:] = []
            continue
        if dp.count(os.sep) - base.count(os.sep) > 5:
            dn[:] = []
        for f in fn:
            if f.startswith('公众号版') or f == 'article.md':
                hits.append(os.path.join(dp, f))
print('HITS:', len(hits))
for h in hits[:80]:
    print(h)
