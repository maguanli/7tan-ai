# -*- coding: utf-8 -*-
"""生成 995 的新字段值，输出 diff 供核对。不改库。"""
import json, re, sys, difflib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

D = json.loads(Path(r'D:\7tan\7tanAI\data\_995_export.json').read_text(encoding='utf-8'))
body = D['ll_baike_body']
orig = body

NEW_SIZE = '419,870,044'
NEW_VER = '1.0.23'
NEW_DATE = '2026-11-01'

# --- 精确片段替换（先做，避免被通则误伤）---
pairs = [
    # 安装包行
    ('官方站点 ZIP（/updates/7tan-editor-free-v1.0.22.zip）；官方页面标 422,663,043 B（约 403 MB），站内条目登记 419,728,173 B（约 400 MB）',
     '官方站点 ZIP（/updates/7tan-editor-free-v1.0.23.zip）；官方页面与站内条目一致，均为 419,870,044 B（约 400 MB）'),
    # 资料边界 ③
    ('③ 包体数据两处轻微出入：官方页面标 <b>422,663,043 B</b>，站内条目登记 <b>419,728,173 B</b>。<b>以官方页面为准</b>。',
     '③ 包体数据已统一：官方页面与站内条目均为 <b>419,870,044 B</b>（约 400 MB），<b>以官方页面为准</b>。'),
    # 已知限制·更新滞后
    ('<li><b>站内更新记录滞后。</b>站内条目的「更新提示」仍停在 v1.0.20，而软件已到 v1.0.22，<b>以官方页面为准</b>。</li>',
     '<li><b>更新记录已同步。</b>站内条目的「更新提示」已随 v1.0.23 一并更新，与官方页面一致。</li>'),
    # 资料时间范围
    ('（2026 年 8–9 月发布）', '（2026 年 8–11 月发布）'),
]
applied = []
for old, new in pairs:
    n = body.count(old)
    if n == 1:
        body = body.replace(old, new)
        applied.append(('OK', n, old[:45]))
    else:
        applied.append((f'COUNT={n}', n, old[:45]))

# --- 通则替换 ---
misc = [
    ('419,728,173', NEW_SIZE),
    ('422,663,043', NEW_SIZE),
    ('约 403 MB', '约 400 MB'),
    ('2026-09-13', NEW_DATE),
    ('1.0.22', NEW_VER),   # 覆盖 v1.0.22 / 1.0.22
]
misc_report = []
for old, new in misc:
    n = body.count(old)
    body = body.replace(old, new)
    misc_report.append((old, n, new))

print('== 精确片段 ==')
for st, n, s in applied:
    print(f'  [{st}] {s}...')
print('\n== 通则替换 ==')
for old, n, new in misc_report:
    print(f'  {old!r} x{n} -> {new!r}')

print('\n== 残留检查 ==')
for bad in ('1.0.22', '1.0.20', '419,728,173', '422,663,043', '403 MB', '2026-09-13'):
    print(f'  {bad!r}: {body.count(bad)}')

# 输出 unified diff（按段落）
print('\n== 变更行 ==')
ol = orig.splitlines()
nl = body.splitlines()
for line in difflib.unified_diff(ol, nl, lineterm='', n=0):
    if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
        print('  ', line[:200])

Path(r'D:\7tan\7tanAI\data\_995_new_body.txt').write_text(body, encoding='utf-8')
print('\n新 body 已写入 data\\_995_new_body.txt, 长度', len(body))
