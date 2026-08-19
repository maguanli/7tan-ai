# -*- coding: utf-8 -*-
"""检查便携版 Chrome 的 User Data 并修复 restore_on_startup"""
import os, json, glob, shutil, time

# 便携版 chrome 所在目录（从快捷方式得知）
portable_root = r'D:\用户目录\下载\新建文件夹 123\chrome-win'
print('便携版目录存在:', os.path.isdir(portable_root))

# 1. 列出目录内容，找 User Data
print('\n=== 便携版目录内容 ===')
try:
    for fn in os.listdir(portable_root):
        fp = os.path.join(portable_root, fn)
        kind = 'DIR ' if os.path.isdir(fp) else 'FILE'
        print(f'  {kind} {fn}')
except Exception as e:
    print('  列出失败:', e)

# 2. 可能的 User Data 位置
candidates = [
    os.path.join(portable_root, 'User Data'),
    os.path.join(portable_root, 'user_data'),
    os.path.join(portable_root, 'data'),
    os.path.join(portable_root, 'chrome-data'),
]
print('\n=== 查找 User Data ===')
user_data_dir = None
for c in candidates:
    if os.path.isdir(c):
        print(f'  存在: {c}')
        user_data_dir = c
        break

# 如果没有，向上找一层
if not user_data_dir:
    parent = os.path.dirname(portable_root)
    print(f'  上级目录 {parent}:')
    try:
        for fn in os.listdir(parent):
            print('   ', fn)
    except Exception as e:
        print('   列出失败:', e)
    for fn in os.listdir(parent):
        if 'user' in fn.lower() or 'data' in fn.lower():
            p = os.path.join(parent, fn)
            if os.path.isdir(p):
                print(f'  候选数据目录: {p}')
                user_data_dir = p

if user_data_dir:
    pref = os.path.join(user_data_dir, 'Default', 'Preferences')
    print(f'\n=== Preferences: {pref} ===')
    print('存在:', os.path.exists(pref))
    if os.path.exists(pref):
        size = os.path.getsize(pref)
        print('大小:', size, '字节')
        try:
            with open(pref, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print('restore_on_startup =', data.get('session', {}).get('restore_on_startup'))
            print('exit_type =', data.get('session', {}).get('exit_type'))
            print('exited_cleanly =', data.get('profile', {}).get('exited_cleanly'))
        except Exception as e:
            print('读取失败:', e)
