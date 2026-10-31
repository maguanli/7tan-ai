# -*- coding: utf-8 -*-
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

d = json.load(open(r'D:\7tan\7tanAI\data\_995_export.json', encoding='utf-8'))
body = d['ll_baike_body']
print('body len =', len(body))
print()
# 找出所有含 1.0.2x / 数字包体 / 日期 的位置
pats = ['1.0.22', '1.0.20', '419,728,173', '422,663,043', '403 MB', '400 MB',
        '2026-09-13', '2026 年 8–9 月', '更新提示', '滞后']
for p in pats:
    idxs = [m.start() for m in re.finditer(re.escape(p), body)]
    print(f'{p!r}: {len(idxs)} 次  at {idxs[:20]}')
print()
print('---- 尾部 2500 字符 ----')
print(body[-2500:])
