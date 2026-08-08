# -*- coding: utf-8 -*-
"""清理 QQ 窗口层级：关闭资料卡，隐藏多余窗口，只留主窗口"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32

# 1. 关闭资料卡窗口 (198950) - 发送 WM_CLOSE
WM_CLOSE = 0x0010
user32.PostMessageW(198950, WM_CLOSE, 0, 0)
print('已发送 WM_CLOSE 给资料卡窗口')
time.sleep(1)

# 2. 隐藏多余的 QQ 窗口 (133534, 198776, 1182034, 199126)
for hwnd in [133534, 198776, 1182034, 199126]:
    user32.ShowWindow(hwnd, 0)  # SW_HIDE
    print(f'已隐藏窗口 {hwnd}')
time.sleep(0.5)

# 3. 显示并激活主窗口 657662
user32.ShowWindow(657662, 9)  # SW_RESTORE
time.sleep(0.3)
user32.SetForegroundWindow(657662)
time.sleep(0.5)
print('主窗口已激活')

# 4. 截图确认状态
with mss_shot() if False else __import__('mss').mss() as sct:
    region = {'left': 480, 'top': 200, 'width': 1060, 'height': 640}
    shot = sct.grab(region)
    from mss.tools import to_png
    to_png(shot.rgb, shot.size, output=r'data\screenshots\qq_clean.png')
print('已保存 qq_clean.png')
