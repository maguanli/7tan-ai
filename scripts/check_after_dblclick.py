# -*- coding: utf-8 -*-
"""检查双击后QQ窗口底部的输入框状态"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import psutil
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

user32 = ctypes.windll.user32

# 直接截当前窗口底部
img = pyautogui.screenshot(region=(480, 700, 1060, 140))
img.save(r'D:\7tan\7tanAI\scripts\qq_after_dblclick_bottom.png')

eng = RapidOCR()
result, _ = eng(np.array(img))
print(f'底部识别 {len(result) if result else 0} 行:')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 700
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')

# 顶部也看一下
img2 = pyautogui.screenshot(region=(480, 200, 1060, 100))
img2.save(r'D:\7tan\7tanAI\scripts\qq_after_dblclick_top.png')
result2, _ = eng(np.array(img2))
print(f'\n顶部识别 {len(result2) if result2 else 0} 行:')
if result2:
    for box, text, score in result2:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 200
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
