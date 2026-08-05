# -*- coding: utf-8 -*-
"""等待微信窗口出现并置顶"""
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

wechat = None
for i in range(20):
    for hwnd, t, cls in enum_all():
        if '微信' in t:
            wechat = hwnd
            break
    if wechat:
        break
    time.sleep(1.5)

if wechat:
    print('找到微信窗口:', wechat)
    win32gui.ShowWindow(wechat, win32con.SW_MAXIMIZE)
    time.sleep(0.5)
    win32gui.SetForegroundWindow(wechat)
    print('rect:', win32gui.GetWindowRect(wechat))
    time.sleep(1.5)
    img = pyautogui.screenshot()
    img.save(r"D:\7tan\7tanAI\check4.png")
    print('saved check4.png')
else:
    print('20秒内未找到微信窗口')
    img = pyautogui.screenshot()
    img.save(r"D:\7tan\7tanAI\check4.png")
    print('saved check4.png (无微信)')
