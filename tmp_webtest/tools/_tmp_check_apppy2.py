# -*- coding: utf-8 -*-
"""分析 src/ui/app.py 空行分布模式"""
import os, re

path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'ui', 'app.py'))
with open(path, encoding='utf-8', errors='replace') as f:
    lines = f.read().split('\n')

total = len(lines)
print(f'total={total}')

# 1) 每500行空行密度
print('--- 空行密度(每500行) ---')
for start in range(0, total, 500):
    seg = lines[start:start+500]
    blank = sum(1 for l in seg if l.strip() == '')
    bar = '#' * int(blank / 5)
    print(f'  行{start+1}-{start+len(seg)}: 空{blank}/{len(seg)} ({blank/len(seg)*100:.0f}%) {bar}')

# 2) 模式：代码行后是否紧跟空行（单行代码行比例）
print('--- 单行代码(独立成行的语句)统计 ---')
single_line = 0
for i, l in enumerate(lines):
    s = l.strip()
    if s and not s.startswith(('#', '"""', "'''")):
        # 粗略判断是否为"短语句行"：不含括号嵌套（不在函数调用内部）
        if len(s) < 120 and not s.endswith(('{', '(', ':', '=', '+', ',', '\\')):
            if s in ('pass', 'break', 'continue', 'return', 'return None'):
                single_line += 1
print(f'  短语句行数: {single_line}')

# 3) 相邻空行块统计（每块2行以上空行的位置分布）
print('--- 空行块(>=2)位置分布 ---')
blocks = []
cur_start = None
cur = 0
for i, l in enumerate(lines):
    if l.strip() == '':
        if cur == 0:
            cur_start = i
        cur += 1
    else:
        if cur >= 2:
            blocks.append((cur_start+1, i, cur))
        cur = 0
if cur >= 2:
    blocks.append((cur_start+1, total, cur))
print(f'  >=2行空行块数: {len(blocks)}')
# 分布到 10 个区段
zones = [0]*10
for b in blocks:
    zone = min(int((b[0]-1) / total * 10), 9)
    zones[zone] += 1
for z in range(10):
    print(f'  区段{z*10}-{(z+1)*10}%: {zones[z]}块')

# 4) 检查是否存在重复行序列（疑似粘贴重复）
print('--- 重复行检测(连续5行完全相同块) ---')
seen = {}
dups = 0
for i in range(total - 5):
    key = tuple(l.strip() for l in lines[i:i+5])
    if all(k for k in key):
        if key in seen:
            dups += 1
            if dups <= 5:
                print(f'  重复块 行{seen[key]+1} 与 行{i+1}: {key[0][:50]}...')
        else:
            seen[key] = i
print(f'  重复块总数: {dups}')

# 5) 文件头尾内容确认
print('--- 头部30行 ---')
for i in range(min(30, total)):
    print(f'{i+1}: {lines[i][:100]}')
