# -*- coding: utf-8 -*-
import json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
st = json.load(open(os.path.join(d, '_mirror_state.json'), encoding='utf-8'))
errors = st.get('errors') or []

mp = os.path.join(d, '_mirror_manifest.ndjson')
mset = set()
with open(mp, encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
            if o.get('url'):
                mset.add(o['url'])
        except Exception:
            pass

print('失败清单里【同时已落盘】的 URL：')
both = [e for e in errors if e['url'] in mset]
for e in both:
    msg = e['error']
    if 'getaddrinfo' in msg:
        cat = 'DNS'
    elif 'WinError 32' in msg:
        cat = '占用'
    elif 'WinError 2' in msg:
        cat = '找不到'
    else:
        cat = msg[:30]
    print('  [%s] %s' % (cat, e['url']))

print()
print('失败清单里【未落盘】的 URL：')
only = [e for e in errors if e['url'] not in mset]
for e in only:
    msg = e['error']
    cat = 'DNS' if 'getaddrinfo' in msg else ('占用' if 'WinError 32' in msg else ('找不到' if 'WinError 2' in msg else msg[:30]))
    print('  [%s] %s' % (cat, e['url']))
print()
print('已落盘 %d / 未落盘 %d' % (len(both), len(only)))
