# -*- coding: utf-8 -*-
"""确认微信窗口位置 + 检查点击点窗口 + 用 SendInput 原生点击"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32
HWND = 329388

# 1. 当前窗口位置
rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'微信窗口 rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})')

# 2. 点击点(785,480)最上层窗口
for px, py in [(785, 480), (740, 480), (700, 480), (785, 400), (900, 500)]:
    hwnd_at = user32.WindowFromPoint(wintypes.POINT(px, py))
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd_at, buf, 256)
    print(f'点({px},{py}): hwnd={hwnd_at} title={buf.value!r}')

# 3. 原生 SendInput 点击（模拟真实硬件点击）
import struct

def send_input_click(x, y):
    """用 SendInput 发送真实鼠标点击"""
    # 移动鼠标
    pyautogui.moveTo(x, y)
    time.sleep(0.3)
    # 左键按下+抬起
    pyautogui.mouseDown(button='left')
    time.sleep(0.15)
    pyautogui.mouseUp(button='left')
    print(f'SendInput 点击 ({x},{y})')

# 激活窗口
user32.SetForegroundWindow(HWND)
time.sleep(0.8)
send_input_click(785, 480)
time.sleep(2.0)
print('完成点击')
