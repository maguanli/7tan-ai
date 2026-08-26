# -*- coding: utf-8 -*-
"""排查打包问题：插件目录、环境引擎清单、打包配置"""
import os, sys

ROOT = r'D:\7tan\7tanAI'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("1. 根目录下 插件/引擎 相关条目")
print("=" * 60)
for x in os.listdir(ROOT):
    low = x.lower()
    if 'plugin' in low or 'engine' in low or '引擎' in x or '插件' in x or 'whitelist' in low or 'manifest' in low:
        full = os.path.join(ROOT, x)
        kind = 'DIR ' if os.path.isdir(full) else 'FILE'
        print(f"  [{kind}] {x}")

print()
print("=" * 60)
print("2. 查找插件目录（常见位置）")
print("=" * 60)
candidates = [
    r'D:\7tan\7tanAI\src\plugins',
    r'D:\7tan\7tanAI\plugins',
    r'D:\7tan\7tanAI\src\core\plugins',
    r'D:\7tan\7tanAI\src\utils\plugins',
]
for c in candidates:
    if os.path.isdir(c):
        items = os.listdir(c)
        print(f"  FOUND DIR: {c}  ({len(items)} 项)")
        for it in items[:60]:
            print(f"     - {it}")
    else:
        print(f"  (不存在) {c}")

print()
print("=" * 60)
print("3. 递归找 plugin 相关目录")
print("=" * 60)
for base, dirs, files in os.walk(ROOT):
    # 跳过 node_modules / .git / dist / build 等
    parts = base.lower().split(os.sep)
    if any(skip in parts for skip in ['node_modules', '.git', 'dist', 'build', '__pycache__', 'downloads', 'data', 'video', 'audio', 'images', 'logs']):
        continue
    for d in dirs:
        if 'plugin' in d.lower() or 'engine' in d.lower():
            print(f"  {os.path.join(base, d)}")
    if base.count(os.sep) - ROOT.count(os.sep) > 3:
        dirs[:] = []
print()
print("DONE")
