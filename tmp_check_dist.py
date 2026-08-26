# -*- coding: utf-8 -*-
"""检查 dist/7tan-editor/_internal/data/plugins 实际结构 + 环境引擎 UI 数据源"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = r'D:\7tan\7tanAI\dist\7tan-editor\_internal\data\plugins'
print("=" * 60)
print("dist/_internal/data/plugins 实际结构")
print("=" * 60)
if not os.path.isdir(base):
    print("  不存在:", base)
else:
    for plug in ['web_search', 'deep_analysis', 'desktop_bot']:
        p = os.path.join(base, plug)
        print(f"--- {plug} ---")
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                rel = os.path.relpath(root, base)
                print(f"  DIR: {rel}  files={files[:8]}")
        else:
            print("  (不是目录)")

print()
print("=" * 60)
print("环境引擎 UI 数据来源（app.py 2685 附近）")
print("=" * 60)
fp = r'D:\7tan\7tanAI\src\ui\app.py'
txt = open(fp, encoding='utf-8', errors='ignore').read()
lines = txt.splitlines()
for i in range(2670, min(2800, len(lines))):
    if '环境引擎' in lines[i] or 'installed_software' in lines[i] or 'software' in lines[i].lower() and 'api' in lines[i].lower():
        print(f"  {i+1}: {lines[i].strip()[:150]}")
print()
print("搜索 app.py 中 环境引擎 tab 的构建/刷新函数")
for i, line in enumerate(lines):
    if '环境引擎' in line and ('def ' in line or 'refresh' in line.lower() or 'load' in line.lower()):
        print(f"  {i+1}: {line.strip()[:150]}")
print("DONE")
