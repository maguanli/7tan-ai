# -*- coding: utf-8 -*-
"""最小化所有非微信窗口 + 微信最大化置顶"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con

def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

wechat_hwnd = None
for hwnd, t, cls in enum_all():
    if '微信' in t and cls not in ('Progman', 'Shell_TrayWnd'):
        wechat_hwnd = hwnd
        continue
    # 跳过桌面/任务栏
    if cls in ('Progman', 'Shell_TrayWnd', 'WorkerW', 'Button'):
        continue
    if not t.strip():
        continue
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        print('minimized:', t[:50], hwnd)
    except Exception as e:
        print('fail:', t[:50], e)

time.sleep(0.8)

if wechat_hwnd:
    win32gui.ShowWindow(wechat_hwnd, win32con.SW_MAXIMIZE)
    time.sleep(0.5)
    win32gui.SetForegroundWindow(wechat_hwnd)
    print('wechat maximized & foreground:', wechat_hwnd)
    print('rect:', win32gui.GetWindowRect(wechat_hwnd))

time.sleep(1.0)
import pyautogui
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\clean2.png")
print('saved clean2.png')
