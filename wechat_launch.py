# -*- coding: utf-8 -*-
"""查找微信exe并启动，唤回微信窗口"""
import sys, io, os, time, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

candidates = [
    r"C:\Program Files\Tencent\Weixin\Weixin.exe",
    r"C:\Program Files (x86)\Tencent\Weixin\Weixin.exe",
    r"C:\Program Files\Tencent\WeChat\WeChat.exe",
    r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Tencent\Weixin\Weixin.exe"),
    r"D:\Program Files\Tencent\WeChat\WeChat.exe",
    r"D:\Program Files\Tencent\Weixin\Weixin.exe",
    r"D:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    r"D:\Program Files (x86)\Tencent\Weixin\Weixin.exe",
]

found = None
for p in candidates:
    if os.path.exists(p):
        found = p
        print('找到:', p)
        break

if not found:
    # 从注册表找
    import winreg
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WeChat"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Tencent\WeChat"),
    ]
    for hive, key in keys:
        try:
            with winreg.OpenKey(hive, key) as k:
                v, _ = winreg.QueryValueEx(k, 'InstallLocation')
                exe = os.path.join(v, 'WeChat.exe')
                if os.path.exists(exe):
                    found = exe
                    print('注册表找到:', exe)
                    break
        except Exception as e:
            pass

if found:
    subprocess.Popen([found], shell=False)
    print('已启动:', found)
    time.sleep(5)
else:
    print('未找到微信exe，请手动打开微信')
