# -*- coding: utf-8 -*-
"""获取微信窗口位置尺寸 + 前台窗口"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con

# 微信窗口
hwnd = win32gui.FindWindow(None, '微信')
if hwnd:
    rect = win32gui.GetWindowRect(hwnd)
    print('微信 rect:', rect, '宽:', rect[2]-rect[0], '高:', rect[3]-rect[1])
    print('微信 visible:', win32gui.IsWindowVisible(hwnd))
    print('微信 minimized:', win32gui.IsIconic(hwnd))
else:
    print('未找到微信窗口')
    # 枚举所有窗口找微信
    def cb(h, _):
        t = win32gui.GetWindowText(h)
        if t and ('微信' in t or 'WeChat' in t):
            print('候选窗口:', h, repr(t), win32gui.GetWindowRect(h))
    win32gui.EnumWindows(cb, None)

# 前台窗口
fg = win32gui.GetForegroundWindow()
print('前台窗口:', fg, repr(win32gui.GetWindowText(fg)), win32gui.GetWindowRect(fg) if fg else '')
