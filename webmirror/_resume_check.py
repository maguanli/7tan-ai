# -*- coding: utf-8 -*-
"""安全核算：确认续抓后待抓 URL 不会被 _visited 拦掉。只读。"""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TDIR = os.path.join(r'D:\7tan\7tanAI\webmirror\downloads', '20261011-063926-4ba5eb')
JOURNAL = os.path.join(TDIR, '_mirror_queue.ndjson')
MANIFEST = os.path.join(TDIR, '_mirror_manifest.ndjson')
STATE = os.path.join(TDIR, '_mirror_state.json')

st = json.load(open(STATE, encoding='utf-8'))
visited = set(st.get('visited') or [])
print('state.visited         =', len(visited))

journal = {}
with open(JOURNAL, encoding='utf-8', errors='replace') as f:
    for line in f:
        p = line.rstrip('\n').split('\t', 2)
        if len(p) == 3 and p[2].startswith(('http://', 'https://')):
            journal.setdefault(p[2], True)
print('journal urls          =', len(journal))

done = set()
with open(MANIFEST, encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get('url'):
            done.add(e['url'])
print('manifest done         =', len(done))

pending = [u for u in journal if u not in done]
print('pending               =', len(pending))

# 关键：pending 里有多少仍在 visited 中（若被 discard 掉就是 0 风险）
p_in_v = sum(1 for u in pending if u in visited)
print()
print('pending ∩ visited     =', p_in_v, '  <- 这些会被当"已处理"跳过')
print('discard 后 pending 可抓 =', len(pending) - p_in_v)

# 反查：visited 与 journal 是否同一套字符串
v_sample = list(visited)[:3]
print()
print('visited 样例:', v_sample)
print('journal 样例:', list(journal)[:3])
same = len(set(journal) & visited)
print('journal ∩ visited     =', same, '（若≈899319，说明同一套字符串）')
