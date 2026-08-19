# -*- coding: utf-8 -*-
import os, json, shutil, subprocess, time, glob

# 真实用户数据目录
UD = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data'
print('User Data 存在:', os.path.exists(UD))
default = os.path.join(UD, 'Default')
print('Default 存在:', os.path.exists(default))

if not os.path.exists(default):
    print('!!! Default 不存在，列出 User Data 内容:')
    if os.path.exists(UD):
        print(os.listdir(UD))
    exit()

pref = os.path.join(default, 'Preferences')

# 1. 备份
bak = pref + '.bak_fix'
if not os.path.exists(bak):
    shutil.copy2(pref, bak)
    print('已备份 ->', bak)

# 2. 修改 Preferences: restore_on_startup = 1 (恢复上次会话)
try:
    with open(pref, 'r', encoding='utf-8') as f:
        content = f.read()
    data = json.loads(content)
    
    # 关键：restore_on_startup 枚举值
    # 1 = 继续上次浏览 (continue where you left off)
    # 4 = 打开特定网页
    # 5 = 打开新标签页
    s = data.setdefault('session', {})
    old_val = s.get('restore_on_startup')
    s['restore_on_startup'] = 1
    s.pop('startup_urls', None)
    s.pop('restore_urls', None)
    
    # 标记上次正常退出，防止被当成崩溃
    profile = data.setdefault('profile', {})
    profile['exit_type'] = 'Normal'
    profile['exited_cleanly'] = True
    
    with open(pref, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print(f'restore_on_startup: {old_val} -> 1 (继续上次浏览)')
    print('exit_type -> Normal, exited_cleanly -> True')
except Exception as e:
    print('修改失败:', e)

# 3. 清理 journal 文件（锁文件，防止Chrome忽略修改）
for jf in glob.glob(pref + '*'):
    if jf.endswith('.journal'):
        try:
            os.remove(jf)
            print('删除锁文件:', jf)
        except Exception as e:
            print('删除失败:', jf, e)

# 4. 确认修改结果
with open(pref, 'r', encoding='utf-8') as f:
    d2 = json.load(f)
print('\n=== 修改后确认 ===')
print('restore_on_startup =', d2.get('session', {}).get('restore_on_startup'))
print('exit_type =', d2.get('profile', {}).get('exit_type'))

# 5. 检查 Sessions 恢复数据
sess = os.path.join(default, 'Sessions')
print('\nSessions 目录:', '存在' if os.path.exists(sess) else '不存在')
if os.path.exists(sess):
    print('文件:', os.listdir(sess))

# 6. 检查 Current Session / Current Tabs
for f in ['Current Session', 'Current Tabs', 'Last Session', 'Last Tabs']:
    fp = os.path.join(default, f)
    print(f, ':', os.path.exists(fp), os.path.getsize(fp) if os.path.exists(fp) else '')
