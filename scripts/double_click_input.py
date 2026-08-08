# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

user32 = ctypes.windll.user32
user32.SetForegroundWindow(657662)
time.sleep(0.3)

# 双击输入框多个位置，看哪个能激活
for attempt, (x, y) in enumerate([(1100, 740), (1050, 750), (1150, 745), (1000, 740)]):
    # 双击
    pyautogui.doubleClick(x, y, interval=0.15)
    time.sleep(0.4)
    pyperclip.copy(f'TRY{attempt}-ABC')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    print(f'第{attempt+1}次: 双击 ({x},{y}) 并粘贴 TRY{attempt}-ABC')
