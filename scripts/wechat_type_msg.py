# -*- coding: utf-8 -*-
"""在 7坛游戏社区 聊天窗口输入并发送问候"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

user32 = ctypes.windll.user32
HWND = 329388

# 1. 激活微信窗口
user32.SetForegroundWindow(HWND)
time.sleep(0.8)

# 2. 点击聊天输入框（窗口底部）
# 窗口 rect (600,292)-(1040,772)，输入框在底部 y≈720-740，x 中间
pyautogui.click(780, 725)
time.sleep(1.0)
print('OK: 已点击输入框 (780,725)')

# 3. 粘贴问候语
msg = ('嗨，7坛游戏社区的朋友们好！👋 我是CodeLion，给大家问个好～'
       '最近站上有什么好玩的新游戏推荐吗？祝大家游戏愉快，7坛越办越火！🎮🔥')
pyperclip.copy(msg)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)
print('OK: 已粘贴问候语')

# 4. 截图确认输入框内容（不发送）
print('MSG_READY')
