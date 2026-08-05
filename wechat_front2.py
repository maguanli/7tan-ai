# -*- coding: utf-8 -*-
"""移走7Tan(不恢复) -> 微信置顶 -> 验证前台"""
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

# 移走 7Tan
for hwnd, t, cls in enum_all():
    if '7Tan' in t:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            rect = win32gui.GetWindowRect(hwnd)
            win32gui.MoveWindow(hwnd, -12000, -12000, rect[2]-rect[0], rect[3]-rect[1], True)
            print('7Tan移走:', t, hwnd)
        except Exception as e:
            print('失败', e)

# 微信置顶
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
    print('微信:', wechat, win32gui.GetWindowRect(wechat))
print('前台:', win32gui.GetWindowText(win32gui.GetForegroundWindow()))

img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\front_ok.png")
print('saved front_ok.png')
