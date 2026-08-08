# -*- coding: utf-8 -*-
"""查找微信安装位置"""
import winreg, os, glob, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

keys = [r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall']
found_reg = []
for root in keys:
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root)
        for i in range(winreg.QueryInfoKey(k)[0]):
            try:
                sub = winreg.EnumKey(k, i)
                sk = winreg.OpenKey(k, sub)
                try:
                    name = winreg.QueryValueEx(sk, 'DisplayName')[0]
                except Exception:
                    name = ''
                if '微信' in str(name) or 'WeChat' in str(name):
                    try:
                        loc = winreg.QueryValueEx(sk, 'InstallLocation')[0]
                    except Exception:
                        loc = ''
                    try:
                        icon = winreg.QueryValueEx(sk, 'DisplayIcon')[0]
                    except Exception:
                        icon = ''
                    found_reg.append((name, loc, icon))
                    print('REG:', name, '|', loc, '|', icon)
            except Exception:
                pass
    except Exception as e:
        print('ERR', root, e)

print('--- 开始菜单快捷方式 ---')
for base in [os.path.join(os.environ.get('ProgramData', r'C:\ProgramData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
             os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')]:
    for pat in ['**/*微信*.lnk', '**/*WeChat*.lnk']:
        for lnk in glob.glob(os.path.join(base, pat), recursive=True):
            print('LNK:', lnk)

print('--- 常见路径 ---')
cands = [
    r'C:\Program Files\Tencent\WeChat\WeChat.exe',
    r'C:\Program Files (x86)\Tencent\WeChat\WeChat.exe',
    r'D:\Program Files\Tencent\WeChat\WeChat.exe',
    r'D:\Tencent\WeChat\WeChat.exe',
    r'C:\Program Files\Tencent\Weixin\Weixin.exe',
    r'C:\Program Files (x86)\Tencent\Weixin\Weixin.exe',
    r'D:\Program Files\Tencent\Weixin\Weixin.exe',
    r'D:\Tencent\Weixin\Weixin.exe',
    os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', '微信.lnk'),
    os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'WeChat.lnk'),
    r'C:\Users\Public\Desktop\微信.lnk',
]
for p in cands:
    if os.path.exists(p):
        print('EXISTS:', p)

print('--- 进程检查 ---')
r = os.popen('tasklist /FI "IMAGENAME eq WeChat.exe" /FO CSV 2>nul').read()
r2 = os.popen('tasklist /FI "IMAGENAME eq Weixin.exe" /FO CSV 2>nul').read()
print('WeChat.exe:', r.strip() or '无')
print('Weixin.exe:', r2.strip() or '无')
print('DONE')
