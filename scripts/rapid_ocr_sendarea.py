# -*- coding: utf-8 -*-
"""RapidOCR 识别窗口最底部区域，找输入框占位符"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image
import pyautogui
import ctypes

user32 = ctypes.windll.user32
QQ_HWND = 1443834
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)

import time
time.sleep(0.5)

# 截取发送按钮附近区域：x 480-1540, y 700-840
img = pyautogui.screenshot(region=(480, 700, 1060, 140))
img.save(r'D:\7tan\7tanAI\scripts\qq_send_area.png')

eng = RapidOCR()
arr = np.array(img)
result, _ = eng(arr)
print(f'识别 {len(result) if result else 0} 行 (绝对y=700~840):')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        cx = int((min(xs) + max(xs)) / 2) + 480
        cy = int((min(ys) + max(ys)) / 2) + 700
        print(f'  ({cx:4d},{cy:4d}) {text}  score={score:.2f}')
else:
    print('无文字')
