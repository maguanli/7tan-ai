# -*- coding: utf-8 -*-
"""对比 dev 构建 _internal 与 _python 构建 _internal 的文件差异"""
import os

out = r'D:\7tan\7tanAI\_tmp_dir_diff.txt'
result = []

# 找 dev 构建的 _internal
dev_internal = None
for root, dirs, files in os.walk(r'D:\7tan\7tanAI\build'):
    if root.endswith('_internal') and os.path.exists(os.path.join(root, 'src')):
        dev_internal = root
        break
    # 限制深度
    if root.count(os.sep) - r'D:\7tan\7tanAI\build'.count(os.sep) > 4:
        dirs[:] = []

cur_internal = r'D:\7tan\7tanAI\dist\7tan-editor\_internal'

result.append('DEV _internal: %s' % dev_internal)
result.append('CUR _internal: %s' % cur_internal)
result.append('')

if not dev_internal:
    # 找 build 目录结构
    for root, dirs, files in os.walk(r'D:\7tan\7tanAI\build'):
        depth = root.count(os.sep)
        if depth <= 5:
            result.append('  DIR: %s' % root)
        if depth > 6:
            dirs[:] = []
else:
    def scan(base):
        d = {}
        for root, dirs, files in os.walk(base):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), base)
                try:
                    d[rel] = os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        return d

    dev = scan(dev_internal)
    cur = scan(cur_internal)

    only_dev = sorted(set(dev) - set(cur))
    only_cur = sorted(set(cur) - set(dev))
    result.append('=== DEV ONLY (%d) ===' % len(only_dev))
    for f in only_dev[:100]:
        result.append('  %s (%d)' % (f, dev[f]))
    result.append('')
    result.append('=== CUR ONLY (%d) ===' % len(only_cur))
    for f in only_cur[:50]:
        result.append('  %s (%d)' % (f, cur[f]))
    result.append('')
    # 大小差异显著的共同文件
    result.append('=== 大小差异 >50KB 的共同文件 ===')
    for f in sorted(set(dev) & set(cur)):
        diff = abs(dev[f] - cur[f])
        if diff > 50000:
            result.append('  %s: dev=%d cur=%d' % (f, dev[f], cur[f]))

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done')
