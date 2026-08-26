# -*- coding: utf-8 -*-
"""检查 Windows zip 内 7tan-src 插件 + _internal 插件目录完整性 + 找环境引擎"""
import os, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

zp = r'D:\7tan\7tanAI\dist\release\7tan-editor-free-v1.0.15.zip'
print("=" * 70)
print("Windows ZIP 内 7tan-src/data/plugins 插件目录")
print("=" * 70)
with zipfile.ZipFile(zp) as zf:
    names = zf.namelist()
    src_plugins = set()
    internal_plugins = set()
    for n in names:
        parts = n.split('/')
        # 7tan-src/data/plugins/<plugin>/
        if len(parts) >= 4 and parts[0] == '7tan-src' and parts[1] == 'data' and parts[2] == 'plugins':
            src_plugins.add(parts[3])
        # 7tan-editor/_internal/data/plugins/<plugin>/
        if len(parts) >= 5 and parts[0] == '7tan-editor' and parts[1] == '_internal' and parts[2] == 'data' and parts[3] == 'plugins':
            internal_plugins.add(parts[4])
    print(f"  7tan-src/data/plugins 子目录: {len(src_plugins)}")
    print(f"  _internal/data/plugins 子目录: {len(internal_plugins)}")
    print("  src 中缺失（internal 有 src 无）:", sorted(internal_plugins - src_plugins))
    print("  internal 中缺失（src 有 internal 无）:", sorted(src_plugins - internal_plugins))

    print()
    print("  --- 检查 _internal 中每个插件目录的文件数（找空壳插件）---")
    counts = {}
    for n in names:
        parts = n.split('/')
        if len(parts) >= 5 and parts[0] == '7tan-editor' and parts[1] == '_internal' and parts[2] == 'data' and parts[3] == 'plugins':
            plug = parts[4]
            counts.setdefault(plug, 0)
            counts[plug] += 1
    for k in sorted(counts):
        mark = "  <-- 异常少" if counts[k] <= 1 else ""
        print(f"    {k}: {counts[k]} 个文件{mark}")

print()
print("=" * 70)
print("查找 环境引擎：src 下模块 + config 文件 + 启动脚本")
print("=" * 70)
ROOT = r'D:\7tan\7tanAI'
# 1) src 下文件名含 engine
for base, dirs, files in os.walk(os.path.join(ROOT, 'src')):
    for f in files:
        if 'engine' in f.lower():
            print(f"  [src] {os.path.join(base, f)}")
# 2) config 目录内容
cfg = os.path.join(ROOT, 'config')
if os.path.isdir(cfg):
    print("  [config] 文件:")
    for f in sorted(os.listdir(cfg)):
        print(f"    - {f}")
# 3) 启动脚本里引用
for f in ['启动网页版服务(Windows).bat', 'start_web_service.bat', 'web_main.py']:
    fp = os.path.join(ROOT, f)
    if os.path.exists(fp):
        try:
            txt = open(fp, encoding='utf-8', errors='ignore').read()
        except Exception as e:
            print(f"  读取 {f} 失败: {e}")
            continue
        print(f"  [{f}] 前80行:")
        for line in txt.splitlines()[:80]:
            print(f"    {line}")
print("DONE")
