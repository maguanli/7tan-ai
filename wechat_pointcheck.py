# -*- coding: utf-8 -*-
"""检测各坐标处的顶层窗口 + 微信窗口状态"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def window_from_point(x, y):
    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    if hwnd:
        t = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        return hwnd, t, cls, rect
    return None

# 检查几个关键点
for pt in [(180, 48), (150, 270), (1200, 500), (40, 40), (960, 540), (1800, 100)]:
    r = window_from_point(*pt)
    print(f'点{pt}:', r)

# 微信窗口状态
hwnd = 66948
print('\n微信窗口 66948:')
print('  visible:', win32gui.IsWindowVisible(hwnd))
print('  enabled:', win32gui.IsWindowEnabled(hwnd))
print('  iconic:', win32gui.IsIconic(hwnd))
print('  foreground:', win32gui.GetForegroundWindow() == hwnd)
print('  rect:', win32gui.GetWindowRect(hwnd))

# 测试窗口响应性
import ctypes
WM_NULL = 0
result = user32.SendMessageTimeoutW(hwnd, WM_NULL, 0, 0, 2, 3000, ctypes.byref(ctypes.c_ulong()))
print('  SendMessageTimeout result:', result)

# 检查微信所有窗口
def enum_cb(h, _):
    if h != hwnd and win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        if '微信' in t or 'Weixin' in t or 'WeChat' in t:
            print('  其他微信窗口:', h, repr(t), win32gui.GetClassName(h), win32gui.GetWindowRect(h), 'enabled=', win32gui.IsWindowEnabled(h))
win32gui.EnumWindows(enum_cb, None)
