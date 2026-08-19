# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip
import mss
from mss.tools import to_png

user32 = ctypes.windll.user32
user32.ShowWindow(657662, 9)
user32.SetForegroundWindow(657662)
time.sleep(0.5)

# 点击输入框
pyautogui.click(1100, 750)
time.sleep(0.5)

# 粘贴测试文字
pyperclip.copy('TEST-CODE-001')
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)

# 截图
with mss.mss() as sct:
    region = {'left': 850, 'top': 690, 'width': 490, 'height': 150}
    shot = sct.grab(region)
    to_png(shot.rgb, shot.size, output=r'data\screenshots\input_test2.png')
print('已点击输入框并粘贴 TEST-CODE-001，截图已保存')
