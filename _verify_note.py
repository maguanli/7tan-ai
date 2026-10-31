# -*- coding: utf-8 -*-
import io, re

P = r'D:\7tan\dsh-workspace\审计报告修正说明-7tan.com.md'
s = io.open(P, encoding='utf-8').read()

print('=== 残留检查（应全为 0）===')
for bad in ['64,403', '296 条', '| 296 |', '686 行', '24 个 finding', '9/36', '5/35', '| 9 |', '| 5 | 14%',
            '我无法复核的两条', '六条措辞偏差', '其余 9 月各日']:
    print(f'  {bad!r}: {s.count(bad)}')

print()
print('=== 应存在的新值 ===')
for good in ['64,404', '297', '685 行', '19 个 finding', '8/36', '4/35', '八个', '五条措辞偏差',
             'ALIBABA-CLOUD---HK', '2006-05-28', '2027-05-28', 'client transfer prohibited',
             '3,154', '首页页脚 0 处', '未含 og:image']:
    print(f'  {good!r}: {s.count(good)}')

print()
print('=== lastmod 表格算术复核 ===')
m = re.search(r'\| 2026-09-09 \| 60,488.*?\| \*\*合计\*\* \| \*\*([\d,]+)\*\*', s, re.S)
block = re.search(r'(\| 2026-09-09 \| 60,488.*?\| \*\*合计\*\* \|[^\n]*)', s, re.S)
if block:
    lines = [l for l in block.group(1).split('\n') if l.strip().startswith('|')]
    nums = []
    for l in lines:
        cells = [c.strip() for c in l.strip('|').split('|')]
        v = cells[1].replace(',', '').replace('*', '')
        if v.isdigit():
            nums.append((cells[0], int(v)))
    print('  明细行:')
    total_decl = None
    run = 0
    for name, v in nums:
        if name.startswith('**合计**'):
            total_decl = v
        else:
            run += v
            print(f'    {name}: {v}')
    print(f'  各行相加 = {run}')
    print(f'  声明合计 = {total_decl}')
    print(f'  一致: {run == total_decl}')
    # 百分比
    print('  百分比校验:')
    ssum = 0
    for name, v in nums:
        if not name.startswith('**合计**'):
            pct = v * 100.0 / total_decl
            ssum += pct
            print(f'    {name}: {pct:.1f}%')
    print(f'  百分比合计 = {ssum:.1f}%')

print()
print('=== 章节结构 ===')
for h in re.findall(r'^## .*$', s, re.M):
    print('  ', h)
print()
print('标题层级数:', len(re.findall(r'^## ', s, re.M)), '/', len(re.findall(r'^### ', s, re.M)))
print('总行数:', s.count('\n') + 1)
print('字符数:', len(s))
