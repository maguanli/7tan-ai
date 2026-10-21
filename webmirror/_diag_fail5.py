# -*- coding: utf-8 -*-
import json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
st = json.load(open(os.path.join(d, '_mirror_state.json'), encoding='utf-8'))
errors = st.get('errors') or []
want = {e['url']: e['error'] for e in errors}

hits = {}
mp = os.path.join(d, '_mirror_manifest.ndjson')
with open(mp, encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line or 'id_' not in line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        u = o.get('url')
        if u in want:
            hits.setdefault(u, []).append(o)

for u, msg in want.items():
    cat = 'DNS' if 'getaddrinfo' in msg else ('占用' if 'WinError 32' in msg else ('找不到' if 'WinError 2' in msg else '其他'))
    rows = hits.get(u)
    if rows:
        r = rows[-1]
        print('[%s] %s' % (cat, u))
        print('      -> 清单有记录: path=%s size=%s status=%s  (共%d条)' % (r.get('path'), r.get('size'), r.get('status'), len(rows)))
    else:
        print('[%s] %s' % (cat, u))
        print('      -> 清单无记录（磁盘上确实没有）')
