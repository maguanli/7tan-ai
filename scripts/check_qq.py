# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def walk_dir(base, max_depth=8):
    if not os.path.exists(base):
        print(f'[不存在] {base}')
        return
    print(f'=== {base} ===')
    try:
        for item in sorted(os.listdir(base)):
            p = os.path.join(base, item)
            kind = 'DIR ' if os.path.isdir(p) else 'FILE'
            print(kind, item)
    except Exception as e:
        print('err:', e)

for base in [r'C:\Program Files\Tencent', r'C:\Program Files (x86)\Tencent', r'C:\Tencent', r'D:\Tencent']:
    walk_dir(base)

# 全盘找 QQ 相关 exe（限常见位置）
print('\n=== 搜索 qq.exe / QQNT ===')
candidates = [
    r'C:\Program Files\Tencent',
    r'C:\Program Files (x86)\Tencent',
    r'D:\Program Files\Tencent',
    r'D:\Program Files (x86)\Tencent',
    r'C:\Users\Administrator\AppData\Local\Programs',
    r'C:\Users\Administrator\AppData\Roaming\Tencent',
    r'C:\Users\Administrator\AppData\Local\Tencent',
]
for base in candidates:
    if not os.path.exists(base):
        continue
    for root, dirs, files in os.walk(base):
        depth = root.count(os.sep)
        if depth > 10:
            dirs[:] = []
            continue
        try:
            for f in files:
                if f.lower() in ('qq.exe', 'qqnt.exe', 'tim.exe', 'wechat.exe'):
                    print('EXE:', os.path.join(root, f))
            for d in dirs:
                if 'qq' in d.lower():
                    print('QQDIR:', os.path.join(root, d))
        except Exception:
            pass

print('\n=== 完成 ===')
