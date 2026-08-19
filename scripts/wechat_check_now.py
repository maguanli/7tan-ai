# -*- coding: utf-8 -*-
"""重新激活微信窗口，检查当前状态"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui, subprocess

# 微信进程还活着吗
r = subprocess.run(['tasklist'], capture_output=True, text=True, encoding='gbk', errors='ignore')
weixin_alive = any('weixin' in l.lower() for l in r.stdout.splitlines())
print('微信进程存活:', weixin_alive)

def find_wechat():
    wins = []
    def cb(h, out):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and ('微信' in t or 'Weixin' in t or 'WeChat' in t):
                out.append((h, t))
    win32gui.EnumWindows(cb, wins)
    return wins

wins = find_wechat()
print('微信窗口:', wins)
if not wins:
    print('未找到微信窗口'); sys.exit(1)
hwnd = wins[0][0]
rect = win32gui.GetWindowRect(hwnd)
print('窗口rect:', rect)
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.3)
win32gui.SetForegroundWindow(hwnd)
time.sleep(1.0)
rect2 = win32gui.GetWindowRect(hwnd)
print('激活后rect:', rect2)

# 截图微信窗口区域
img = pyautogui.screenshot(region=(max(0,rect2[0]), max(0,rect2[1]), min(1920,rect2[2])-max(0,rect2[0]), min(1080,rect2[3])-max(0,rect2[1])))
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_now.png")
print('已保存 wechat_now.png:', img.size)
