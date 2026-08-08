# -*- coding: utf-8 -*-
"""检查重建后的QQ窗口395876底部布局：输入框/发送按钮"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from rapidocr_onnxruntime import RapidOCR
import numpy as np

user32 = ctypes.windll.user32
QQ_HWND = 395876
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)

eng = RapidOCR()

# 底部区域 y=640~840
img = pyautogui.screenshot(region=(480, 640, 1060, 200))
img.save(r'D:\7tan\7tanAI\scripts\qq_395876_bottom.png')
result, _ = eng(np.array(img))
print('=== 窗口底部 y=640~840 ===')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 640
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
else:
    print('  无文字')

# 左侧区域验证（之前透出7Tan内容）
img2 = pyautogui.screenshot(region=(480, 200, 400, 300))
img2.save(r'D:\7tan\7tanAI\scripts\qq_395876_left.png')
result2, _ = eng(np.array(img2))
print('\n=== 窗口左侧 x=480~880, y=200~500 ===')
if result2:
    for box, text, score in result2:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 200
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
else:
    print('  无文字')
