# -*- coding: utf-8 -*-
import json, os, io, sys, collections, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
mp = os.path.join(d, '_mirror_manifest.ndjson')

print('=== 清单里的 HTTP 状态码分布 ===')
codes = collections.Counter()
n = 0
with open(mp, encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            o = json.loads(line)
        except Exception:
            continue
        codes[o.get('status')] += 1
print('清单条数:', n)
for k, v in sorted(codes.items(), key=lambda x: -x[1]):
    print('   HTTP %-6s : %d' % (k, v))
bad = sum(v for k, v in codes.items() if isinstance(k, int) and k >= 400)
print('   >=400 的条目（被当成功保存下来了）:', bad)

print()
print('=== 磁盘上残留的 .part 临时文件 ===')
parts = glob.glob(os.path.join(d, '**', '*.part'), recursive=True)
print('.part 文件数:', len(parts))
for p in parts[:10]:
    print('   ', os.path.relpath(p, d), os.path.getsize(p), 'bytes')

print()
print('=== 目录体积 ===')
tot = 0
for root, dirs, files in os.walk(d):
    for fn in files:
        try:
            tot += os.path.getsize(os.path.join(root, fn))
        except Exception:
            pass
print('总字节: %d (%.2f GB)' % (tot, tot/1024/1024/1024))
