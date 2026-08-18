# -*- coding: utf-8 -*-
"""临时检查脚本：统计 app.py 行数/空行/结构，判定是否损坏"""
import os, sys

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'ui', 'app.py')
path = os.path.normpath(path)

with open(path, encoding='utf-8', errors='replace') as f:
    raw = f.read()

lines = raw.split('\n')
total = len(lines)
blank = sum(1 for l in lines if l.strip() == '')
code = total - blank

print(f'文件: {path}')
print(f'总行数: {total}')
print(f'空行数: {blank} ({blank/total*100:.1f}%)')
print(f'代码行: {code}')

# 统计连续空行段
max_run = 0
cur = 0
runs = []
for i, l in enumerate(lines):
    if l.strip() == '':
        cur += 1
        if cur > max_run:
            max_run = cur
    else:
        if cur >= 5:
            runs.append((i - cur + 1, i, cur))  # (起始行, 结束行, 长度)
        cur = 0
print(f'最大连续空行: {max_run}')
print(f'连续>=5空行的段数: {len(runs)}')
for r in runs[:20]:
    print(f'  段: 行{r[0]}-{r[1]} 长度{r[2]}')

# 语法检查
import ast
try:
    ast.parse(raw)
    print('语法检查: OK (ast.parse 通过)')
except SyntaxError as e:
    print(f'语法检查: FAIL -> {e}')

# 行号分布抽样（每1000行取一行看内容）
print('--- 抽样（每1000行）---')
for i in range(0, total, 1000):
    content = lines[i].strip()
    print(f'  行{i+1}: {content[:80] if content else "(空)"}')
