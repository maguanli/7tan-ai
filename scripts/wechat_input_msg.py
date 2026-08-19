# -*- coding: utf-8 -*-
"""点击聊天输入框并粘贴问候语（大窗口版）"""
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

user32.SetForegroundWindow(HWND)
time.sleep(0.8)

# 点击输入框：窗口(400,200)-(1300,850)，右侧聊天区 x 700-1300，输入框在底部 y≈750-820
pyautogui.click(1000, 790)
time.sleep(1.2)
print('OK: 已点击输入框 (1000,790)')

# 检查是否又弹出对话框（前台窗口变化检查）
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: {buf.value!r}')
if '选择' in buf.value or '文件' in buf.value:
    print('WARN: 又弹出对话框！')
    pyautogui.press('esc')
    time.sleep(1.0)

# 粘贴问候语
msg = ('嗨，7坛游戏社区的朋友们好！👋 我是CodeLion，给大家问个好～'
       '最近站上有什么好玩的新游戏推荐吗？祝大家游戏愉快，7坛越办越火！🎮🔥')
pyperclip.copy(msg)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)
print('OK: 已粘贴问候语，等待OCR确认')
