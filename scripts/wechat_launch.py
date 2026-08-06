# -*- coding: utf-8 -*-
"""查找微信安装路径并启动"""
import os, subprocess, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 常见安装路径
candidates = [
    r'C:\Program Files\Tencent\WeChat\WeChat.exe',
    r'C:\Program Files\Tencent\Weixin\Weixin.exe',
    r'C:\Program Files (x86)\Tencent\WeChat\WeChat.exe',
    r'C:\Program Files (x86)\Tencent\Weixin\Weixin.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe'),
    os.path.expandvars(r'%LOCALAPPDATA%\Tencent\Weixin\Weixin.exe'),
]

# 注册表查询（更可靠）
def find_from_registry():
    try:
        import winreg
        keys = [
            (winreg.HKEY_CURRENT_USER, r'Software\Tencent\WeChat'),
            (winreg.HKEY_CURRENT_USER, r'Software\Tencent\Weixin'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\WeChat'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WeChat'),
        ]
        for hive, path in keys:
            try:
                k = winreg.OpenKey(hive, path)
                try:
                    val, _ = winreg.QueryValueEx(k, 'InstallPath')
                    if val and os.path.exists(val):
                        for exe in ('WeChat.exe', 'Weixin.exe'):
                            p = os.path.join(val, exe)
                            if os.path.exists(p):
                                return p
                except OSError:
                    pass
                winreg.CloseKey(k)
            except OSError:
                continue
    except Exception as e:
        print('注册表查询失败:', e)
    return None

path = find_from_registry()
if not path:
    for p in candidates:
        if os.path.exists(p):
            path = p
            break

if not path:
    print('未找到微信安装路径，请手动启动微信')
else:
    print('找到微信:', path)
    # 启动
    try:
        subprocess.Popen([path], shell=False)
        print('已启动微信，等待窗口出现...')
        time.sleep(6)
        # 再次扫描窗口
        import win32gui
        wins = []
        def cb(hwnd, out):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    out.append((hwnd, t))
        win32gui.EnumWindows(cb, wins)
        found = False
        for h, t in wins:
            if '微信' in t or 'Weixin' in t or 'WeChat' in t:
                print('窗口出现:', h, repr(t))
                found = True
        if not found:
            print('窗口尚未出现（可能还在加载或需要扫码）')
    except Exception as e:
        print('启动失败:', e)
