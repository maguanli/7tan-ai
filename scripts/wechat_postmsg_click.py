# -*- coding: utf-8 -*-
"""用 PostMessage 直接向微信窗口发送鼠标点击（绕过焦点问题）"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

HWND = 329388
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

def post_click(hwnd, x, y):
    """x,y 为窗口客户区坐标"""
    lparam = (y << 16) | (x & 0xFFFF)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    time.sleep(0.1)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
    print(f'OK: PostMessage 点击 ({x},{y})')

# 微信窗口 rect (50,100)，客户区坐标 = 屏幕坐标 - 左上角
# "7坛游戏" 条目：屏幕 (220,270) → 客户区 (170,170)
post_click(HWND, 170, 170)
time.sleep(2.0)
print('已点击 7坛游戏 条目')
