# -*- coding: utf-8 -*-
"""把 7Tan 窗口最小化，微信窗口置顶，确认微信可见"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

def find_windows(title_part):
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if title_part in t:
                out.append((hwnd, t))
    win32gui.EnumWindows(cb, None)
    return out

# 1. 最小化 7Tan 窗口（标题含 '7Tan' 且不是 '7Tan — AI工具' 外的其他，找最大的那个）
for hwnd, t in find_windows('7Tan'):
    print('7Tan window:', t, hwnd)
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        print('  minimized')
    except Exception as e:
        print('  fail', e)

time.sleep(0.8)

# 2. 微信窗口恢复并置顶
for hwnd, t in find_windows('微信'):
    print('WeChat window:', t, hwnd)
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        print('  restored & foreground')
        break
    except Exception as e:
        print('  fail', e)

time.sleep(1.5)

# 3. 截图确认
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\front_check.png")
print('saved front_check.png', img.size)
