# -*- coding: utf-8 -*-
"""检查已发布 zip 内的插件数量与环境引擎清单"""
import os, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

zips = [
    r'D:\7tan\7tanAI\dist\release\7tan-editor-free-v1.0.15.zip',
    r'D:\7tan\7tanAI\dist\release\7tan-web-v1.0.15.zip',
]

for zp in zips:
    print("=" * 70)
    print(f"ZIP: {os.path.basename(zp)}")
    if not os.path.exists(zp):
        print("  不存在！")
        continue
    print(f"  大小: {os.path.getsize(zp)/1048576:.1f} MB")
    try:
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
            print(f"  总条目: {len(names)}")
            # 统计 data/plugins 下的插件目录（含 tools.py 或 plugin.json 的目录）
            plugin_dirs = set()
            plugin_files = []
            for n in names:
                if '/data/plugins/' in n or n.startswith('data/plugins/'):
                    plugin_files.append(n)
                    parts = n.split('/')
                    # 找到 data/plugins 后第一个子目录
                    try:
                        idx = parts.index('plugins')
                        if len(parts) > idx + 1:
                            plugin_dirs.add(parts[idx + 1])
                    except ValueError:
                        pass
            print(f"  data/plugins 相关条目: {len(plugin_files)}")
            print(f"  插件一级子目录: {len(plugin_dirs)}")
            for d in sorted(plugin_dirs):
                print(f"    - {d}")
            # 检查环境引擎清单文件
            print("  --- 引擎/清单相关文件 ---")
            for n in names:
                low = n.lower()
                if any(k in low for k in ['engine', 'environ', 'manifest', 'requirement', '清单']):
                    print(f"    {n}")
    except Exception as e:
        print(f"  读取失败: {e}")
    print()

print("=" * 70)
print("源码里查找 环境引擎 相关文件")
print("=" * 70)
ROOT = r'D:\7tan\7tanAI'
for base, dirs, files in os.walk(ROOT):
    parts = base.lower().split(os.sep)
    if any(s in parts for s in ['node_modules', '.git', 'dist', 'build', '__pycache__', 'downloads', 'video', 'audio', 'images', 'logs', '.venv']):
        continue
    depth = base.count(os.sep) - ROOT.count(os.sep)
    for f in files:
        if 'engine' in f.lower() or 'environ' in f.lower():
            print(f"  {os.path.join(base, f)}")
print("DONE")
