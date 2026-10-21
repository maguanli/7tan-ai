# -*- coding: utf-8 -*-
import json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
st = json.load(open(os.path.join(d, '_mirror_state.json'), encoding='utf-8'))
errors = st.get('errors') or []

print('=== 流水账首行（确认格式）===')
jp = os.path.join(d, '_mirror_queue.ndjson')
with open(jp, encoding='utf-8', errors='replace') as f:
    for _ in range(3):
        print('   ', repr(f.readline()[:160]))

# 按 TSV 解析
jset = set()
n = 0
bad = 0
with open(jp, encoding='utf-8', errors='replace') as f:
    for line in f:
        n += 1
        parts = line.rstrip('\n').split('\t', 2)
        if len(parts) != 3:
            bad += 1
            continue
        u = parts[2]
        if u.startswith(('http://', 'https://')):
            jset.add(u)
print()
print('流水账行数        %d' % n)
print('  格式不符行       %d' % bad)
print('  唯一 URL(曾入队) %d' % len(jset))

in_j = [e['url'] for e in errors if e['url'] in jset]
print()
print('失败 URL 共 %d，其中仍在流水账(曾入队)里 %d' % (len(errors), len(in_j)))

# manifest 里有没有（落盘=成功）
mp = os.path.join(d, '_mirror_manifest.ndjson')
mset = set()
if os.path.exists(mp):
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
print('清单(已落盘)唯一 URL %d' % len(mset))
in_m = sum(1 for e in errors if e['url'] in mset)
print('失败 URL 里已落盘的（应为0）%d' % in_m)
print()
print('结论：失败 URL 仍留在流水账、不在清单 → 下次续抓会重新排队（会被重试）'
      if len(in_j) == len(errors) and in_m == 0 else '结论：与预期不符，见上')
