# -*- coding: utf-8 -*-
import os, subprocess, json, sys

# 1. 读取桌面快捷方式真实目标
print('=== 1. chrome.exe.lnk 快捷方式内容 ===')
lnk = r'C:\Users\Administrator\Desktop\chrome.exe.lnk'
ps = f'''$s=(New-Object -ComObject WScript.Shell).CreateShortcut("{lnk}"); Write-Output ("Target=" + $s.TargetPath); Write-Output ("Args=" + $s.Arguments); Write-Output ("WorkDir=" + $s.WorkingDirectory)'''
r = subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True, encoding='gbk', errors='replace', timeout=20)
print(r.stdout)
print(r.stderr[:500])

# 2. 检查 Google Chrome 目录是否存在
print('\n=== 2. Google Chrome 相关目录 ===')
for p in [r'C:\Users\Administrator\AppData\Local\Google',
          r'C:\Users\Administrator\AppData\Local\Google\Chrome',
          r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data',
          r'C:\Program Files\Google\Chrome\Application\chrome.exe']:
    print(p, '->', '存在' if os.path.exists(p) else '不存在')

# 3. 查找真正 Chrome 安装位置
print('\n=== 3. 查找 chrome.exe 安装位置 ===')
for root, dirs, files in os.walk(r'C:\Program Files'):
    if 'chrome.exe' in files:
        print('找到:', os.path.join(root, 'chrome.exe'))
    if root.count(os.sep) - r'C:\Program Files'.count(os.sep) > 3:
        dirs[:] = []
for root, dirs, files in os.walk(r'C:\Program Files (x86)'):
    if 'chrome.exe' in files:
        print('找到:', os.path.join(root, 'chrome.exe'))
    if root.count(os.sep) - r'C:\Program Files (x86)'.count(os.sep) > 3:
        dirs[:] = []
for root, dirs, files in os.walk(r'C:\Users\Administrator\AppData\Local'):
    if 'chrome.exe' in files:
        print('找到:', os.path.join(root, 'chrome.exe'))
    if root.count(os.sep) - r'C:\Users\Administrator\AppData\Local'.count(os.sep) > 3:
        dirs[:] = []

# 4. 检查 360Chrome 的 Preferences 设置
print('\n=== 4. 360Chrome/2345Chrome 的启动设置 ===')
for ud in [r'C:\Users\Administrator\AppData\Local\360Chrome\Chrome\User Data',
           r'C:\Users\Administrator\AppData\Local\360ChromeX\Chrome\User Data',
           r'C:\Users\Administrator\AppData\Local\2345chrome\User Data']:
    if os.path.exists(ud):
        for prof in ['Default']:
            pref = os.path.join(ud, prof, 'Preferences')
            if os.path.exists(pref):
                try:
                    d = json.load(open(pref, encoding='utf-8'))
                    s = d.get('session', {})
                    print(f'{ud}\\{prof}: restore_on_startup={s.get("restore_on_startup")} exit_type={s.get("exit_type")}')
                except Exception as e:
                    print(f'{ud}\\{prof}: 读取失败 {e}')
