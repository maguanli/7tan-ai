# -*- coding: utf-8 -*-
"""对比 _python 环境 与 开发机 .venv 的已安装包"""
import subprocess, sys, os

out = r'D:\7tan\7tanAI\_tmp_env_diff.txt'
result = []

# 1. _python 环境
py_portable = r'D:\7tan\7tanAI\dist\_python\python.exe'
r1 = subprocess.run([py_portable, '-m', 'pip', 'list', '--format=freeze'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
portable_pkgs = {}
for line in r1.stdout.splitlines():
    line = line.strip()
    if '==' in line:
        name, ver = line.rsplit('==', 1)
        portable_pkgs[name.lower()] = ver
result.append('=== _python portable (%d pkgs) ===' % len(portable_pkgs))

# 2. 开发机 python（当前环境）
r2 = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=freeze'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
dev_pkgs = {}
for line in r2.stdout.splitlines():
    line = line.strip()
    if '==' in line:
        name, ver = line.rsplit('==', 1)
        dev_pkgs[name.lower()] = ver
result.append('=== dev python (%d pkgs) ===' % len(dev_pkgs))

# 3. 差异：dev 有而 portable 没有
missing = sorted(set(dev_pkgs) - set(portable_pkgs))
result.append('')
result.append('=== DEV HAS, PORTABLE MISSING (%d) ===' % len(missing))
for m in missing:
    result.append('  %s==%s' % (m, dev_pkgs[m]))

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done, missing:', len(missing))
