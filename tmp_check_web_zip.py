# -*- coding: utf-8 -*-
"""专项检查：web zip 与 src 包里的插件数量 + 环境引擎清单"""
import os, sys, zipfile, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

zp = r'D:\7tan\7tanAI\dist\release\7tan-web-v1.0.15.zip'
print("=" * 70)
print(f"WEB ZIP: {os.path.basename(zp)}")
if not os.path.exists(zp):
    print("  不存在！")
else:
    print(f"  大小: {os.path.getsize(zp)/1048576:.1f} MB")
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        print(f"  总条目: {len(names)}")
        plugin_dirs = set()
        for n in names:
            parts = n.split('/')
            if 'data' in parts and 'plugins' in parts:
                idx = parts.index('plugins')
                if len(parts) > idx + 1:
                    plugin_dirs.add(parts[idx + 1])
        print(f"  data/plugins 一级子目录: {len(plugin_dirs)}")
        for d in sorted(plugin_dirs):
            print(f"    - {d}")
        print()
        print("  根目录文件:")
        for n in names:
            if n.count('/') == 0:
                print(f"    {n}")
        print()
        print("  引擎/清单相关:")
        for n in names:
            low = n.lower()
            if ('engine' in low or 'environ' in low or 'manifest' in low) and ('dll' not in low and 'qml' not in low and 'pak' not in low):
                print(f"    {n}")

print()
print("=" * 70)
print("源码 data/plugins 中 6 个插件 vs 46 个：检查 hashes/installed/manifest")
print("=" * 70)
pdir = r'D:\7tan\7tanAI\data\plugins'
for f in ['installed.json', 'adapt_status.json', 'adapt_report.json']:
    fp = os.path.join(pdir, f)
    if os.path.exists(fp):
        try:
            data = json.load(open(fp, encoding='utf-8'))
            s = json.dumps(data, ensure_ascii=False)
            print(f"  {f}: {s[:500]}")
        except Exception as e:
            print(f"  {f}: 读取失败 {e}")

print()
print("=" * 70)
print("搜索 '环境引擎' 相关代码/文件")
print("=" * 70)
ROOT = r'D:\7tan\7tanAI'
for base, dirs, files in os.walk(ROOT):
    parts = base.lower().split(os.sep)
    if any(s in parts for s in ['node_modules', '.git', 'dist', 'build', '__pycache__', 'downloads', 'video', 'audio', 'images', 'logs', '.venv', 'data\\tmp']):
        continue
    depth = base.count(os.sep) - ROOT.count(os.sep)
    if depth > 2:
        dirs[:] = []
        continue
    for f in files:
        if f.endswith(('.json', '.txt', '.md', '.yaml', '.yml', '.ini')):
            fp = os.path.join(base, f)
            try:
                txt = open(fp, encoding='utf-8', errors='ignore').read(3000)
            except Exception:
                continue
            if '环境引擎' in txt or '引擎安装' in txt or 'engine_install' in txt.lower() or '环境安装' in txt:
                print(f"  {fp}")
                # 打印含关键词的行
                for line in txt.splitlines():
                    if '环境引擎' in line or '引擎安装' in line or 'engine_install' in line.lower() or '环境安装' in line:
                        print(f"      >> {line.strip()[:120]}")
print("DONE")
