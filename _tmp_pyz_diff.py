# -*- coding: utf-8 -*-
"""对比开发机 PYZ 与 _python PYZ 的大小，并列出 _python 构建缺失的关键模块"""
import os, zipfile, re

out = r'D:\7tan\7tanAI\_tmp_pyz_diff.txt'
result = []

dev_pyz = r'D:\7tan\7tanAI\build\build\PYZ-00.pyz'
cur_pyz = r'D:\7tan\7tanAI\dist\_build\temp\build\PYZ-00.pyz'

result.append('DEV PYZ: %s (%d bytes)' % (dev_pyz, os.path.getsize(dev_pyz) if os.path.exists(dev_pyz) else -1))
result.append('CUR PYZ: %s (%d bytes)' % (cur_pyz, os.path.getsize(cur_pyz) if os.path.exists(cur_pyz) else -1))
result.append('')

# PYZ 是 zip 格式
def list_pyz(p):
    names = set()
    try:
        with zipfile.ZipFile(p) as z:
            names = set(z.namelist())
    except Exception as e:
        result.append('  open fail %s: %s' % (p, e))
    return names

dev_names = list_pyz(dev_pyz)
cur_names = list_pyz(cur_pyz)
result.append('DEV modules: %d, CUR modules: %d' % (len(dev_names), len(cur_names)))
result.append('')

# 开发机有而当前没有的模块（排除 __pycache__）
only_dev = sorted(n for n in (dev_names - cur_names) if not n.startswith('__pycache__'))
result.append('=== DEV ONLY (%d) ===' % len(only_dev))
for n in only_dev[:120]:
    result.append('  ' + n)

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done, only_dev:', len(only_dev))
