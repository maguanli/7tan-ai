# -*- coding: utf-8 -*-
"""清理窗口 -> 置顶微信登录窗 -> 截取二维码"""
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

# 最小化所有非微信窗口
for hwnd, t, cls in enum_all():
    if '微信' in t:
        continue
    if cls in ('Progman', 'Shell_TrayWnd', 'WorkerW'):
        continue
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    except Exception:
        pass

time.sleep(0.8)

# 微信登录窗口置顶
wx = None
for hwnd, t, cls in enum_all():
    if '微信' in t:
        wx = hwnd
        break
if wx:
    win32gui.ShowWindow(wx, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(wx)
    time.sleep(1.0)
    rect = win32gui.GetWindowRect(wx)
    print('微信登录窗:', wx, rect)
    # 截取登录窗口放大
    x, y = rect[0], rect[1]
    w, h = rect[2]-rect[0], rect[3]-rect[1]
    img = pyautogui.screenshot(region=(max(x,0), max(y,0), w, h))
    img = img.resize((img.width * 2, img.height * 2))
    img.save(r"D:\7tan\7tanAI\wechat_login_qr2.png")
    print('二维码已保存: D:\\7tan\\7tanAI\\wechat_login_qr2.png', img.size)
