# -*- coding: utf-8 -*-
"""检查QQ进程 + 枚举所有窗口，找出QQ当前状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import subprocess, win32gui, win32process, win32api

# 1) QQ 进程
print('--- QQ processes ---')
r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq QQ.exe', '/FO', 'CSV'],
                   capture_output=True, text=True, encoding='gbk', errors='replace')
print(r.stdout.strip() or 'NO QQ.exe')

# 2) 所有可见窗口标题含QQ的
print('--- windows with QQ in title/class ---')
wins = []
def cb(hwnd, extra):
    if not win32gui.IsWindowVisible(hwnd):
        return True
    t = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    if t.strip() or 'Chrome' in cls:
        try:
            rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            rect = None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pid = -1
        wins.append((hwnd, pid, cls, t.strip(), rect))
    return True
win32gui.EnumWindows(cb, None)
for h, pid, cls, t, r in wins:
    if 'QQ' in t or 'QQ' in cls or 'Chrome' in cls or '7723' in t:
        print(f'{h} | pid={pid} | {cls} | {t!r} | {r}')
print('--- all visible windows count:', len(wins))
for h, pid, cls, t, r in wins:
    print(f'{h} | pid={pid} | {cls} | {t!r} | {r}')
