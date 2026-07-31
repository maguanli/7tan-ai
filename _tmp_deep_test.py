# -*- coding: utf-8 -*-
"""深度测试：比较开发机构建的 exe 与 _python 构建的 exe 差异 + 完整启动测试"""
import os, subprocess, time

out = r'D:\7tan\7tanAI\_tmp_deep_test.txt'
result = []

# 1. 找开发机构建的 exe（21.5MB）
dev_exe = None
for root, dirs, files in os.walk(r'D:\7tan\7tanAI'):
    # 跳过 dist、.venv、node_modules
    if any(x in root for x in ('.venv', 'node_modules', '_tmp', '__pycache__')):
        continue
    for f in files:
        if f == '7tan-editor.exe' and 'dist' not in root:
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
            except Exception:
                continue
            result.append('FOUND exe: %s (%d bytes)' % (p, sz))
            if sz > 20000000:
                dev_exe = p

result.append('DEV EXE (>20MB): %s' % dev_exe)
result.append('')

# 2. 当前 _python 构建的 exe
cur_exe = r'D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe'
result.append('CURRENT EXE: %s (%d bytes)' % (cur_exe, os.path.getsize(cur_exe)))
result.append('')

# 3. 对比 _internal 目录文件列表差异
if dev_exe:
    dev_dir = os.path.dirname(dev_exe)
    dev_internal = os.path.join(dev_dir, '_internal')
    cur_internal = os.path.join(os.path.dirname(cur_exe), '_internal')
    if os.path.exists(dev_internal) and os.path.exists(cur_internal):
        dev_files = {}
        for root, dirs, files in os.walk(dev_internal):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), dev_internal)
                dev_files[rel.lower()] = os.path.getsize(os.path.join(root, f))
        cur_files = {}
        for root, dirs, files in os.walk(cur_internal):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), cur_internal)
                cur_files[rel.lower()] = os.path.getsize(os.path.join(root, f))

        only_dev = sorted(set(dev_files) - set(cur_files))
        only_cur = sorted(set(cur_files) - set(dev_files))
        result.append('=== 开发机有、当前没有 (%d) ===' % len(only_dev))
        for f in only_dev[:80]:
            result.append('  %s (%d)' % (f, dev_files[f]))
        result.append('')
        result.append('=== 当前有、开发机没有 (%d) ===' % len(only_cur))
        for f in only_cur[:40]:
            result.append('  %s (%d)' % (f, cur_files[f]))

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done')
