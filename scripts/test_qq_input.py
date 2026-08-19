# -*- coding: utf-8 -*-
"""测试QQ输入框：点击输入框 -> 粘贴测试文字 -> 截图验证"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import pyperclip
import time
import mss
from PIL import Image

# 1. 点击输入框
INPUT_X, INPUT_Y = 1050, 850
print(f'点击输入框 @ ({INPUT_X},{INPUT_Y})')
pyautogui.click(INPUT_X, INPUT_Y)
time.sleep(0.8)

# 2. 粘贴测试文字
test_text = '输入框功能测试-123'
pyperclip.copy(test_text)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1)

# 3. 截图验证
with mss.mss() as sct:
    monitor = sct.monitors[0]
    img = sct.grab(monitor)
    pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
    # 只截输入框区域放大
    box = (780, 800, 1360, 900)
    crop = pil.crop(box)
    crop = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    crop.save(r"scripts\qq_input_test.png")
    pil.save(r"scripts\qq_input_test_full.png")
print('已保存输入框截图: scripts/qq_input_test.png')
print('DONE')
