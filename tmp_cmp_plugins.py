# -*- coding: utf-8 -*-
"""对比：源码 data/plugins 各插件文件数 vs zip 内条目路径细节"""
import os, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PDIR = r'D:\7tan\7tanAI\data\plugins'
print("=" * 70)
print("源码 data/plugins 各插件目录文件数（前 60）")
print("=" * 70)
for d in sorted(os.listdir(PDIR)):
    full = os.path.join(PDIR, d)
    if not os.path.isdir(full):
        continue
    n = sum(len(fs) for _, _, fs in os.walk(full))
    print(f"  {d}: {n} 文件")
    if n <= 1:
        for _, _, fs in os.walk(full):
            print(f"      -> {fs}")

print()
print("=" * 70)
print("ZIP 内 web_search / deep_analysis 的完整条目（看是否嵌套重复）")
print("=" * 70)
zp = r'D:\7tan\7tanAI\dist\release\7tan-editor-free-v1.0.15.zip'
with zipfile.ZipFile(zp) as zf:
    names = zf.namelist()
    for plug in ['web_search', 'deep_analysis', 'iching', 'desktop_bot']:
        print(f"  --- {plug} ---")
        cnt = 0
        for n in names:
            if f'_internal/data/plugins/{plug}/' in n:
                print(f"    {n}")
                cnt += 1
        if cnt == 0:
            print("    (无条目)")

print()
print("=" * 70)
print("源码中 '环境引擎' / '引擎' 功能搜索（src 下 py 文件）")
print("=" * 70)
ROOT = r'D:\7tan\7tanAI'
import re
for base, dirs, files in os.walk(os.path.join(ROOT, 'src')):
    if '__pycache__' in base:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        fp = os.path.join(base, f)
        try:
            txt = open(fp, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for kw in ['环境引擎', '引擎管理', 'engine_manager', '环境安装', 'install_engine']:
            if kw in txt:
                print(f"  {fp} 含关键词: {kw}")
                break
print("DONE")
