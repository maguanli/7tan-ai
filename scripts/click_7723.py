# -*- coding: utf-8 -*-
"""点击7723群，打开聊天窗口"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import time

# 7723手机游戏超级群位置 (OCR: 600,691-731,704)
X, Y = 665, 697
print(f'点击 7723手机游戏超级群 @ ({X},{Y})')
pyautogui.click(X, Y)
time.sleep(2)

# 截图确认
import mss
from PIL import Image
with mss.mss() as sct:
    monitor = sct.monitors[0]
    img = sct.grab(monitor)
    pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
    pil.save(r"scripts\qq_7723_chat.png")
print('已保存截图: scripts/qq_7723_chat.png')
print('DONE')
