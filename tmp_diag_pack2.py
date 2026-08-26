# -*- coding: utf-8 -*-
"""排查：data/plugins 插件数、环境引擎清单、打包配置"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\7tan\7tanAI'

print("=" * 60)
print("1. data 目录结构")
print("=" * 60)
data_dir = os.path.join(ROOT, 'data')
if os.path.isdir(data_dir):
    for x in sorted(os.listdir(data_dir)):
        full = os.path.join(data_dir, x)
        kind = 'DIR ' if os.path.isdir(full) else 'FILE'
        try:
            size = os.path.getsize(full) if os.path.isfile(full) else ''
        except Exception:
            size = ''
        print(f"  [{kind}] {x}  {size}")
else:
    print("  data 目录不存在")

print()
print("=" * 60)
print("2. data/plugins 插件数量")
print("=" * 60)
pdir = os.path.join(data_dir, 'plugins')
if os.path.isdir(pdir):
    items = sorted(os.listdir(pdir))
    dirs = [x for x in items if os.path.isdir(os.path.join(pdir, x))]
    files = [x for x in items if not os.path.isdir(os.path.join(pdir, x))]
    print(f"  总项: {len(items)} | 插件目录: {len(dirs)} | 文件: {len(files)}")
    print("  插件目录列表:")
    for d in dirs:
        print(f"    - {d}")
    print("  文件列表:")
    for f in files:
        print(f"    - {f}")
    # manifest
    mf = os.path.join(pdir, 'manifest.json')
    if os.path.exists(mf):
        try:
            import json
            data = json.load(open(mf, encoding='utf-8'))
            if isinstance(data, list):
                print(f"  manifest.json 插件条目: {len(data)}")
                for p in data:
                    print(f"    id={p.get('id')} name={p.get('name')} type={p.get('type')}")
            elif isinstance(data, dict):
                print(f"  manifest.json keys: {list(data.keys())}")
        except Exception as e:
            print(f"  manifest.json 解析失败: {e}")
else:
    print("  data/plugins 不存在")

print()
print("=" * 60)
print("3. 查找 环境引擎/安装清单 相关文件")
print("=" * 60)
kw = ['engine', 'manifest', 'install', 'environ', 'requirement', '清单', '环境', '引擎']
for base, dirs, files in os.walk(ROOT):
    parts = base.lower().split(os.sep)
    if any(s in parts for s in ['node_modules', '.git', 'dist', 'build', '__pycache__', 'downloads', 'video', 'audio', 'images', 'logs', 'data\\screenshots']):
        continue
    depth = base.count(os.sep) - ROOT.count(os.sep)
    if depth > 2:
        dirs[:] = []
        continue
    for f in files:
        low = f.lower()
        if any(k in low for k in kw) and f.endswith(('.json', '.txt', '.yaml', '.yml', '.ini', '.toml')):
            print(f"  {os.path.join(base, f)}")
print()
print("DONE")
