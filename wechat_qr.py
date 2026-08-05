# -*- coding: utf-8 -*-
"""截取微信登录窗口二维码"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

# 找微信登录窗口
def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

best = None
for hwnd, t, cls in enum_all():
    if '微信' in t or 'Weixin' in t:
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        if w < 800 and h < 800:  # 登录窗口较小
            best = (hwnd, t, rect)
            print('登录窗口:', t, rect, w, h)
            break

if best:
    hwnd, t, rect = best
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    rect = win32gui.GetWindowRect(hwnd)
    x, y, x2, y2 = rect
    img = pyautogui.screenshot(region=(max(x,0), max(y,0), x2-x, y2-y))
    img = img.resize((img.width*2, img.height*2))
    img.save(r"D:\7tan\7tanAI\wechat_login_qr.png")
    print('二维码截图已保存: D:\\7tan\\7tanAI\\wechat_login_qr.png', img.size)
else:
    print('未找到登录窗口')
