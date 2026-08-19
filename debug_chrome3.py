# -*- coding: utf-8 -*-
"""验证便携版 Chrome 的配置状态"""
import os, json, glob

UD = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data'

print('=== 1. Preferences 当前实际值 ===')
pref = os.path.join(UD, 'Default', 'Preferences')
if os.path.exists(pref):
    with open(pref, 'r', encoding='utf-8') as f:
        d = json.load(f)
    print('restore_on_startup =', d.get('session', {}).get('restore_on_startup'))
    print('exit_type =', d.get('profile', {}).get('exit_type'))
    print('exited_cleanly =', d.get('profile', {}).get('exited_cleanly'))
    print('首页urls =', d.get('session', {}).get('startup_urls'))

print('\n=== 2. User Data 下 First Run 是否存在 ===')
fr = os.path.join(UD, 'First Run')
print('First Run 存在:', os.path.exists(fr))
fr2 = r'D:\用户目录\下载\新建文件夹 123\chrome-win\First Run'
print('便携版目录 First Run 存在:', os.path.exists(fr2))

print('\n=== 3. Sessions 目录（会话文件）===')
sess = os.path.join(UD, 'Default', 'Sessions')
if os.path.isdir(sess):
    files = sorted(os.listdir(sess), key=lambda x: os.path.getmtime(os.path.join(sess, x)))
    for fn in files[-6:]:
        fp = os.path.join(sess, fn)
        import datetime
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime('%Y-%m-%d %H:%M:%S')
        print(f'  {fn}  {os.path.getsize(fp)}B  {mt}')
else:
    print('Sessions 目录不存在')

print('\n=== 4. Current Session / Last Session ===')
for fn in ['Current Session', 'Current Tabs', 'Last Session', 'Last Tabs']:
    fp = os.path.join(UD, 'Default', fn)
    print(f'  {fn}: {os.path.exists(fp)}')

print('\n=== 5. chrome.exe.lnk 快捷方式实际参数 ===')
import win32com.client
lnk_path = r'C:\Users\Administrator\Desktop\chrome.exe.lnk'
sh = win32com.client.Dispatch('WScript.Shell')
sc = sh.CreateShortcut(lnk_path)
print('Target:', sc.TargetPath)
print('Args  :', repr(sc.Arguments))
print('WorkDir:', sc.WorkingDirectory)

print('\n=== 6. Chrome 是否正在运行 ===')
out = os.popen('tasklist | findstr /i chrome.exe').read()
print('chrome 进程数:', out.count('chrome.exe') if out else 0)
