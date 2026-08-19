# -*- coding: utf-8 -*-
"""调查 Chrome 真实启动路径与配置文件"""
import os, sys, json, glob, subprocess

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return (r.stdout or '') + (r.stderr or '')
    except Exception as e:
        return f'ERR: {e}'

print('='*60)
print('1. Chrome 进程信息')
print('='*60)
out = run('wmic process where "name=\'chrome.exe\'" get ExecutablePath,CommandLine /format:list')
print(out[:3000] if out else '(无输出)')

print('='*60)
print('2. 桌面快捷方式')
print('='*60)
desktops = [
    os.path.join(os.environ.get('USERPROFILE',''), 'Desktop'),
    r'C:\Users\Public\Desktop',
]
for d in desktops:
    if not os.path.isdir(d):
        continue
    for lnk in glob.glob(os.path.join(d, '*.lnk')):
        print(f'-- {lnk}')
        try:
            import win32com.client
            sh = win32com.client.Dispatch('WScript.Shell')
            sc = sh.CreateShortcut(lnk)
            print(f'   Target: {sc.TargetPath}')
            print(f'   Args  : {sc.Arguments}')
            print(f'   WorkDir: {sc.WorkingDirectory}')
        except Exception as e:
            print(f'   读取失败: {e}')
            # 尝试直接读 lnk 文本
            try:
                with open(lnk, 'rb') as f:
                    data = f.read()
                # 提取其中的路径字符串（ASCII）
                import re
                strs = re.findall(rb'[ -~]{10,300}', data)
                for s in strs[:20]:
                    txt = s.decode('ascii', 'ignore')
                    if 'chrome' in txt.lower() or '.exe' in txt.lower() or 'User Data' in txt:
                        print(f'   LNK文本: {txt}')
            except Exception as e2:
                print(f'   文本读取失败: {e2}')

print('='*60)
print('3. 查找 chrome.exe 位置')
print('='*60)
candidates = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Users\Administrator\AppData\Local\Google\Chrome\Application\chrome.exe',
    r'C:\Users\guanzhishu\AppData\Local\Google\Chrome\Application\chrome.exe',
]
for c in candidates:
    print(('存在  ' if os.path.exists(c) else '不存在'), c)

# 在 D 盘浅层找 chrome.exe
for root in [r'D:\\']:
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.count(os.sep)
        if depth > 4:
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.lower() == 'chrome.exe':
                print('找到:', os.path.join(dirpath, fn))
        if depth >= 4:
            dirnames[:] = []

print('='*60)
print('4. 用户数据目录')
print('='*60)
udirs = [
    r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data',
    r'C:\Users\guanzhishu\AppData\Local\Google\Chrome\User Data',
]
for u in udirs:
    if os.path.isdir(u):
        print(f'存在: {u}')
        pref = os.path.join(u, 'Default', 'Preferences')
        if os.path.exists(pref):
            size = os.path.getsize(pref)
            print(f'   Default\\Preferences: {size} 字节, 修改时间: {os.path.getmtime(pref)}')
        sess = os.path.join(u, 'Default', 'Sessions')
        if os.path.isdir(sess):
            print('   Sessions 目录:')
            for fn in os.listdir(sess):
                fp = os.path.join(sess, fn)
                print(f'      {fn}  {os.path.getsize(fp)}B  {os.path.getmtime(fp)}')
        tabs = os.path.join(u, 'Default', 'Current Session')
        print(f'   Current Session 存在: {os.path.exists(tabs)}')
    else:
        print(f'不存在: {u}')

print('='*60)
print('5. 策略注册表')
print('='*60)
out = run('reg query "HKCU\\Software\\Policies\\Google\\Chrome" 2>nul')
print(out or '(HKCU 无策略)')
out = run('reg query "HKLM\\SOFTWARE\\Policies\\Google\\Chrome" 2>nul')
print(out or '(HKLM 无策略)')
out = run('reg query "HKLM\\SOFTWARE\\WOW6432Node\\Policies\\Google\\Chrome" 2>nul')
print(out or '(WOW6432Node 无策略)')

print('='*60)
print('6. Chrome 版本')
print('='*60)
for c in candidates:
    if os.path.exists(c):
        ver = run(f'powershell -NoProfile -Command "(Get-Item \'{c}\').VersionInfo.ProductVersion"')
        print(f'{c} => {ver.strip()}')
