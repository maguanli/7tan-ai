# -*- coding: utf-8 -*-
"""监控 build_log.txt 是否还在增长 + 尾部内容"""
import os, time

path = r'D:\7tan\7tanAI\dist\build_log.txt'
out = r'D:\7tan\7tanAI\_tmp_log_out.txt'

sizes = []
for i in range(3):
    try:
        sizes.append(os.path.getsize(path))
    except Exception as e:
        sizes.append(-1)
    time.sleep(2)

result = []
result.append('build_log.txt sizes (2s interval): %s' % sizes)
growing = len(set(sizes)) > 1
result.append('GROWING: %s' % growing)

data = open(path, 'rb').read()
text = data.decode('utf-8', errors='replace')
lines = text.splitlines()
result.append('LINES: %d' % len(lines))
result.append('--- TAIL 25 ---')
for l in lines[-25:]:
    result.append('| ' + l)

# 检查是否有 build complete
result.append('')
result.append('HAS "Build complete": %s' % ('Build complete' in text))
result.append('HAS "ERROR": %s' % ('ERROR' in text.upper()))

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done', sizes)
