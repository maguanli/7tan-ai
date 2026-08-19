# -*- coding: utf-8 -*-
"""截取微信窗口画面，确认登录状态"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import win32gui, win32con
import mss

# 找到微信窗口
hwnd = None
def cb(h, out):
    global hwnd
    if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h) == '微信':
        out.append(h)
wins = []
win32gui.EnumWindows(cb, wins)
if wins:
    hwnd = wins[0]
    print('微信窗口句柄:', hwnd)
    # 激活窗口
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(1)
    except Exception as e:
        print('激活窗口失败:', e)
    # 获取窗口位置大小
    rect = win32gui.GetWindowRect(hwnd)
    print('窗口位置:', rect)
    x, y, x2, y2 = rect
    w, h = x2 - x, y2 - y
    # 用 mss 截取该区域
    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        img = sct.grab(monitor)
        from PIL import Image
        im = Image.frombytes('RGB', img.size, img.rgb)
        out_path = r'D:/7tan/7tanAI/data/screenshots/wechat_status.png'
        im.save(out_path)
        print('已保存截图:', out_path, im.size)
else:
    print('未找到微信窗口')
