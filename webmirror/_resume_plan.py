# -*- coding: utf-8 -*-
"""按 crawler._restore_state 的算法，在真实文件上算出「续抓会重新入队多少 URL」。
只读，不修改任何文件。"""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TID = '20261011-063926-4ba5eb'
TDIR = os.path.join(r'D:\7tan\7tanAI\webmirror\downloads', TID)

JOURNAL = os.path.join(TDIR, '_mirror_queue.ndjson')
MANIFEST = os.path.join(TDIR, '_mirror_manifest.ndjson')
STATE = os.path.join(TDIR, '_mirror_state.json')

print('=' * 64)
print('A) state 快照里的 stats（决定续抓起点）')
print('=' * 64)
st = json.load(open(STATE, encoding='utf-8'))
stats = st.get('stats') or {}
for k in sorted(stats.keys()):
    v = stats[k]
    if k in ('started_at', 'finished_at'):
        v = '%.0f' % v if isinstance(v, (int, float)) else v
    print('  %-16s = %s' % (k, v))
print('  visited(len)     =', len(st.get('visited') or []))
print('  queue(len)       =', len(st.get('queue') or []))
print('  saved(len)       =', len(st.get('saved') or {}))

print()
print('=' * 64)
print('B) 流水账 journal（曾入队全部 URL）')
print('=' * 64)
journal_urls = {}
n_line = 0
with open(JOURNAL, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        n_line += 1
        parts = line.rstrip('\n').split('\t', 2)
        if len(parts) != 3:
            continue
        d, k, u = parts
        if not u or u in journal_urls:
            continue
        if not u.startswith(('http://', 'https://')):
            continue
        journal_urls[u] = True
print('  物理行数        =', n_line)
print('  journal 有效URL =', len(journal_urls))

print()
print('=' * 64)
print('C) 清单 manifest（已落盘）')
print('=' * 64)
done = set()
n_man = 0
with open(MANIFEST, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        n_man += 1
        try:
            e = json.loads(line)
        except Exception:
            continue
        u = e.get('url')
        if u:
            done.add(u)
print('  manifest 行数   =', n_man)
print('  manifest 唯一URL=', len(done))

print()
print('=' * 64)
print('D) ★ 续抓会重新入队的 URL 数 = journal − done')
print('=' * 64)
pending = [u for u in journal_urls if u not in done]
print('  pending         =', len(pending))
print()
print('  样例（前 5 个待抓）：')
for u in pending[:5]:
    print('    ', u)

print()
print('=' * 64)
print('E) 上限核算')
print('=' * 64)
cfg = None
tasks = json.load(open(os.path.join(r'D:\7tan\7tanAI\webmirror\downloads', '_tasks.json'), encoding='utf-8'))
for t in tasks:
    if t.get('id') == TID:
        cfg = t.get('config') or {}
        break
cur_max = cfg.get('max_pages') if cfg else None
pt = stats.get('pages_total')
print('  任务现存 max_pages     =', cur_max)
print('  state 里 pages_total   =', pt)
print('  pending 页数           =', len(pending))
need = (pt or 0) + len(pending)
print('  若续抓跑完，pages_total = %s + %s = %s' % (pt, len(pending), need))
print('  结论：需要 max_pages >= %s 才装得下' % need)

print()
print('=' * 64)
print('F) 磁盘')
print('=' * 64)
import shutil
tot, used, free = shutil.disk_usage('D:\\')
print('  D盘 总 %.1f GB / 已用 %.1f GB / 剩余 %.1f GB' % (tot/2**30, used/2**30, free/2**30))
sz = 0
for r, _, fs in os.walk(TDIR):
    for fn in fs:
        try:
            sz += os.path.getsize(os.path.join(r, fn))
        except OSError:
            pass
print('  当前任务目录占用 = %.2f GB' % (sz/2**30))
