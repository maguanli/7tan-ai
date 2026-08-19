# -*- coding: utf-8 -*-
import os, json, glob, shutil

# 用 os.walk 定位 chrome-win 真实路径（避免编码问题）
chrome_win = None
for root, dirs, files in os.walk('D:\\'):
    if root.count(os.sep) > 4:
        dirs[:] = []
        continue
    if 'chrome.exe' in files and 'chrome-win' in root:
        chrome_win = root
        break

if not chrome_win:
    print('未找到 chrome-win')
    exit()

print('真实路径:', chrome_win)
print('目录内容:')
for f in os.listdir(chrome_win):
    fp = os.path.join(chrome_win, f)
    print(' ', '[DIR]' if os.path.isdir(fp) else '[FILE]', f)

# 查找 User Data
print('\n=== 查找 User Data ===')
user_data = None
for cand in [os.path.join(chrome_win, 'User Data'),
             os.path.join(chrome_win, '..', 'User Data'),
             os.path.join(chrome_win, 'Chrome', 'User Data')]:
    cand = os.path.abspath(cand)
    if os.path.exists(cand):
        user_data = cand
        print('找到:', cand)
        break

# 如果没有，搜索上级目录
if not user_data:
    parent = os.path.dirname(chrome_win)
    for f in os.listdir(parent):
        fp = os.path.join(parent, f)
        if os.path.isdir(fp) and ('User' in f or 'data' in f.lower()):
            print('上级目录候选:', fp)
    # 检查 chrome-win 里的所有子目录
    for f in os.listdir(chrome_win):
        fp = os.path.join(chrome_win, f)
        if os.path.isdir(fp):
            sub = os.path.join(fp, 'User Data')
            if os.path.exists(sub):
                print('子目录 User Data:', sub)

# 检查 Default Preferences
if user_data:
    default = os.path.join(user_data, 'Default')
    pref = os.path.join(default, 'Preferences')
    print('\nDefault 目录:', '存在' if os.path.exists(default) else '不存在')
    if os.path.exists(default):
        print('Default 内容:', os.listdir(default)[:20])
    if os.path.exists(pref):
        try:
            d = json.load(open(pref, encoding='utf-8'))
            s = d.get('session', {})
            print('restore_on_startup =', s.get('restore_on_startup'))
            print('exit_type =', s.get('exit_type'))
            print('session keys =', list(s.keys()))
        except Exception as e:
            print('读取失败:', e)
    else:
        print('Preferences 不存在!')

# 保存真实路径到文件供后续使用
with open(r'D:\7tan\7tanAI\chrome_real_path.txt', 'w', encoding='utf-8') as f:
    f.write(chrome_win + '\n')
    f.write(user_data or '')
print('\n真实路径已保存到 chrome_real_path.txt')
