# -*- coding: utf-8 -*-
import os, json, glob

# 便携版 Chrome 目录
base = r'D:\用户目录\资料\新建文件夹 123\chrome-win'
print('=== 便携版目录内容 ===')
if os.path.exists(base):
    for f in os.listdir(base):
        fp = os.path.join(base, f)
        kind = 'DIR' if os.path.isdir(fp) else 'FILE'
        print(f'[{kind}] {f}')
else:
    print('目录不存在!', base)

# 查找 User Data
print('\n=== 查找 User Data ===')
for cand in [os.path.join(base, 'User Data'),
             os.path.join(base, 'Chrome', 'User Data'),
             os.path.join(base, 'data'),
             os.path.join(base, 'Profile')]:
    if os.path.exists(cand):
        print('找到 User Data:', cand)
        # 列出 Default
        default = os.path.join(cand, 'Default')
        if os.path.exists(default):
            print('  Default 存在')
            pref = os.path.join(default, 'Preferences')
            if os.path.exists(pref):
                try:
                    d = json.load(open(pref, encoding='utf-8'))
                    s = d.get('session', {})
                    print(f'  restore_on_startup = {s.get("restore_on_startup")}')
                    print(f'  exit_type = {s.get("exit_type")}')
                except Exception as e:
                    print('  Preferences 读取失败:', e)
            else:
                print('  Preferences 不存在!')
        # 列出所有 profile 目录
        for p in os.listdir(cand):
            if os.path.isdir(os.path.join(cand, p)):
                print('  profile:', p)

# 也检查同盘其他位置
print('\n=== 搜索 chrome-win 附近所有 User Data ===')
for root, dirs, files in os.walk(base):
    if 'User Data' in dirs:
        print('找到:', os.path.join(root, 'User Data'))
    if root.count(os.sep) - base.count(os.sep) > 2:
        dirs[:] = []
