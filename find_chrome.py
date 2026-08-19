# -*- coding: utf-8 -*-
import os, glob, subprocess, sys

print('=== 1. 当前系统用户 ===')
print('USERPROFILE:', os.environ.get('USERPROFILE'))
print('USERNAME:', os.environ.get('USERNAME'))

print('\n=== 2. 查找所有 Chrome 快捷方式 ===')
# 桌面快捷方式
desktops = [os.path.join(os.environ.get('USERPROFILE',''), 'Desktop'),
            os.path.join(os.environ.get('PUBLIC',''), 'Desktop')]
for dt in desktops:
    if os.path.exists(dt):
        for f in os.listdir(dt):
            if 'chrome' in f.lower() or 'Chrome' in f:
                fp = os.path.join(dt, f)
                print('找到:', fp)
                # 用 powershell 读快捷方式目标
                try:
                    r = subprocess.run(['powershell','-NoProfile','-Command',
                        f'$s=(New-Object -ComObject WScript.Shell).CreateShortcut("{fp}"); Write-Output $s.TargetPath; Write-Output $s.Arguments'],
                        capture_output=True, text=True, encoding='utf-8', timeout=15)
                    print('  目标:', r.stdout)
                except Exception as e:
                    print('  读取失败:', e)

print('\n=== 3. 注册表里的 Chrome 安装位置 ===')
for key in [r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
            r'HKCU\Software\Google\Chrome\BLBeacon',
            r'HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe']:
    try:
        r = subprocess.run(['reg','query',key], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
        if r.returncode == 0:
            print(f'[{key}]')
            print(r.stdout)
    except Exception as e:
        print(key, 'err', e)

print('\n=== 4. 搜索常见的 User Data 位置 ===')
candidates = []
for base_dir in [os.environ.get('LOCALAPPDATA',''), os.environ.get('APPDATA',''), r'C:\Program Files\Google', r'C:\Program Files (x86)\Google', 'D:\\', r'D:\Program Files', r'D:\Program Files (x86)', r'C:\Users']:
    if not base_dir or not os.path.exists(base_dir):
        continue
    for root, dirs, files in os.walk(base_dir):
        # 限制深度
        depth = root[len(base_dir):].count(os.sep)
        if depth > 3:
            dirs[:] = []
            continue
        if 'User Data' in dirs and 'chrome.exe' in os.listdir(root) if os.path.exists(root) else False:
            pass
        if 'User Data' in dirs:
            candidates.append(os.path.join(root, 'User Data'))
        # 找 chrome.exe
        if 'chrome.exe' in files:
            print('chrome.exe 位于:', os.path.join(root, 'chrome.exe'))
        if len(candidates) > 5:
            break
    if len(candidates) > 5:
        break

print('找到的 User Data 目录:', candidates)

print('\n=== 5. 检查环境变量 CHROME_USER_DATA / 启动器脚本 ===')
for f in [r'D:\7tan\7tanAI\chrome_launcher.pyw', r'D:\7tan\7tanAI\chrome_fix.py']:
    if os.path.exists(f):
        print(f'--- {f} ---')
        try:
            print(open(f, encoding='utf-8').read()[:1500])
        except Exception as e:
            print('读取失败', e)
