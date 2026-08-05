# -*- coding: utf-8 -*-
"""检查所有窗口状态，把微信拉回前台并截图"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

print('=== 当前可见窗口 ===')
wechat = None
for hwnd, t, cls in enum_all():
    if not t.strip():
        continue
    try:
        rect = win32gui.GetWindowRect(hwnd)
        iconic = win32gui.IsIconic(hwnd)
    except Exception:
        continue
    print(f"{t[:40]!r} cls={cls[:20]} rect={rect} iconic={iconic}")
    if '微信' in t and not iconic:
        wechat = hwnd

# 微信最大化置顶
if wechat:
    win32gui.ShowWindow(wechat, win32con.SW_MAXIMIZE)
    time.sleep(0.5)
    win32gui.SetForegroundWindow(wechat)
    print('wechat max+fg:', wechat)
else:
    # 找任何微信窗口
    for hwnd, t, cls in enum_all():
        if '微信' in t:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(hwnd)
            print('wechat(any) max+fg:', hwnd, t)
            break

time.sleep(1.2)
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\check3.png")
print('saved check3.png')
