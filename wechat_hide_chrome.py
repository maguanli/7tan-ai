# -*- coding: utf-8 -*-
"""最小化所有浏览器 -> 微信置顶 -> 点击测试"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, win32gui, win32con

def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

# 最小化所有非微信窗口（含 Chrome）
for hwnd, t, cls in enum_all():
    if '微信' in t:
        continue
    if cls in ('Progman', 'Shell_TrayWnd', 'WorkerW', 'Button'):
        continue
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        print('minimized:', t[:40], hwnd)
    except Exception:
        pass

time.sleep(0.8)

# 微信恢复+置顶
wechat = None
for hwnd, t, cls in enum_all():
    if '微信' in t:
        wechat = hwnd
        break
if wechat:
    win32gui.ShowWindow(wechat, win32con.SW_MAXIMIZE)
    time.sleep(0.4)
    win32gui.SetForegroundWindow(wechat)
    time.sleep(0.8)
    fg = win32gui.GetForegroundWindow()
    print('微信置顶:', wechat, '前台:', win32gui.GetWindowText(fg))
    # WindowFromPoint 验证
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    h = user32.WindowFromPoint(wintypes.POINT(150, 270))
    print('点(150,270)顶层窗口:', h, win32gui.GetWindowText(h) if h else '')

    # 点击测试
    pyautogui.click(150, 270)
    time.sleep(2.0)
    img = pyautogui.screenshot()
    img.save(r"D:\7tan\7tanAI\after_hide_chrome.png")
    print('saved after_hide_chrome.png')
