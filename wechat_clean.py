# -*- coding: utf-8 -*-
"""最小化除微信外的所有窗口，置顶微信"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

KEEP = ['微信', 'Program Manager', '任务栏']

def enum():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            if t.strip():
                out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

for hwnd, t, cls in enum():
    skip = False
    for k in KEEP:
        if k in t:
            skip = True
            break
    if skip:
        continue
    # 跳过桌面/任务栏类
    if cls in ('Progman', 'Shell_TrayWnd', 'WorkerW'):
        continue
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        print('minimized:', t[:40], hwnd)
    except Exception as e:
        print('fail:', t[:40], e)

time.sleep(1.0)

# 置顶微信
for hwnd, t, cls in enum():
    if '微信' in t:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        print('wechat foreground:', t, hwnd)
        break

time.sleep(1.0)
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\clean_check.png")
print('saved clean_check.png')
