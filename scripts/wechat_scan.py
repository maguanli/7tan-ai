# -*- coding: utf-8 -*-
"""侦察微信客户端环境：进程、窗口、依赖"""
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1. 查找微信进程
r = subprocess.run(['tasklist'], capture_output=True, text=True, encoding='gbk', errors='ignore')
procs = [l for l in r.stdout.splitlines() if 'weixin' in l.lower() or 'wechat' in l.lower()]
print('=== 微信进程 ===')
print('\n'.join(procs) if procs else '未找到微信进程')

# 2. 查找微信窗口
try:
    import win32gui
    def cb(hwnd, out):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t:
                out.append((hwnd, t))
    wins = []
    win32gui.EnumWindows(cb, wins)
    print('=== 微信相关窗口 ===')
    found = False
    for h, t in wins:
        if '微信' in t or 'Weixin' in t or 'WeChat' in t:
            print(h, repr(t))
            found = True
    if not found:
        print('未找到微信窗口（进程可能最小化到托盘）')
except ImportError as e:
    print('pywin32 未安装:', e)

# 3. 检查依赖
print('=== 依赖检查 ===')
for mod in ['pyautogui', 'pyperclip', 'mss', 'PIL', 'win32gui', 'win32clipboard']:
    try:
        __import__(mod)
        print(f'{mod}: OK')
    except ImportError:
        print(f'{mod}: 缺失')
