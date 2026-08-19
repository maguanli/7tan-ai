# -*- coding: utf-8 -*-
"""定位 QQ.exe 并结束所有 QQ 进程"""
import os, subprocess, time, glob

# 1. 定位 QQ.exe
candidates = []
for base in [r'C:\Program Files\Tencent', r'C:\Program Files (x86)\Tencent', os.path.expandvars(r'%LOCALAPPDATA%\Programs')]:
    for root, dirs, files in os.walk(base):
        if 'QQ.exe' in files:
            p = os.path.join(root, 'QQ.exe')
            candidates.append(p)
            print('FOUND:', p)
        # 限制深度，避免遍历过久
        if root.count(os.sep) - base.count(os.sep) > 3:
            dirs.clear()

if not candidates:
    print('未找到 QQ.exe')
else:
    print('使用:', candidates[0])

# 2. 结束所有 QQ 进程
print('\n===== 结束所有 QQ 进程 =====')
result = subprocess.run(['taskkill', '/F', '/IM', 'QQ.exe'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

time.sleep(3)

# 3. 验证是否清理干净
result2 = subprocess.run(['tasklist'], capture_output=True, text=True)
qq_left = [l for l in result2.stdout.splitlines() if 'QQ' in l]
print('===== 剩余 QQ 进程 =====')
print('\n'.join(qq_left) if qq_left else '✅ 已全部清理干净')
