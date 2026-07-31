# -*- coding: utf-8 -*-
"""检查 _python 环境是否满足 requirements.txt"""
import subprocess, re, os

out = r'D:\7tan\7tanAI\_tmp_req_check.txt'
result = []

py = r'D:\7tan\7tanAI\dist\_python\python.exe'
r = subprocess.run([py, '-m', 'pip', 'list', '--format=freeze'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
installed = {}
for line in r.stdout.splitlines():
    line = line.strip()
    if '==' in line:
        name, ver = line.rsplit('==', 1)
        installed[name.lower()] = ver

# 解析 requirements.txt
req_path = r'D:\7tan\7tanAI\dist\_build\requirements.txt'
required = []
with open(req_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # 去掉注释
        line = re.split(r'\s+#', line)[0].strip()
        required.append(line)

result.append('requirements 条目数: %d' % len(required))
result.append('_python 已装包数: %d' % len(installed))
result.append('')
result.append('=== 缺失/未满足 ===')
missing = []
for req in required:
    m = re.match(r'([A-Za-z0-9_.\-]+)', req)
    if not m:
        continue
    pkg = m.group(1).lower().replace('_', '-')
    # 处理 extras: package[extra]
    pkg = pkg.split('[')[0]
    if pkg not in installed:
        missing.append(req)
        result.append('  MISSING: %s' % req)

if not missing:
    result.append('  (全部满足)')

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done, missing:', len(missing))
