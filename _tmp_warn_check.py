# -*- coding: utf-8 -*-
"""检查 PyInstaller warn-build.txt 中的缺失模块"""
import os

out = r'D:\7tan\7tanAI\_tmp_warn_out.txt'
result = []

# 可能的路径
candidates = [
    r'D:\7tan\7tanAI\dist\_build\temp\build\warn-build.txt',
    r'D:\7tan\7tanAI\dist\_build\temp\warn-build.txt',
    r'D:\7tan\7tanAI\dist\_build\warn-build.txt',
]

found = None
for p in candidates:
    if os.path.exists(p):
        found = p
        break

if not found:
    result.append('warn-build.txt NOT FOUND (搜索了: %s)' % candidates)
    # 找一下 temp 目录
    temp_dir = r'D:\7tan\7tanAI\dist\_build\temp'
    if os.path.exists(temp_dir):
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                if 'warn' in f.lower() or 'xref' in f.lower():
                    result.append('FOUND: %s' % os.path.join(root, f))
else:
    result.append('FOUND: %s' % found)
    with open(found, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    lines = text.splitlines()
    result.append('LINES: %d' % len(lines))
    result.append('')
    result.append('=== 缺失模块列表 ===')
    for l in lines:
        result.append('| ' + l)

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done')
