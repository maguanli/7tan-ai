# -*- coding: utf-8 -*-
"""确认恢复后的QQ主窗口 395876 状态，OCR 验证群名"""
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

rect = wt.RECT()
user32.GetWindowRect(QQ_HWND, ctypes.byref(rect))
print(f'窗口 395876: ({rect.left},{rect.top},{rect.right},{rect.bottom}) 尺寸=({rect.right-rect.left}x{rect.bottom-rect.top})')
print(f'可见: {user32.IsWindowVisible(QQ_HWND)}')

# 置顶并激活
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.8)
print(f'前台: {user32.GetForegroundWindow()}')

# 截图并 OCR 顶部（群名）
img = pyautogui.screenshot(region=(rect.left, rect.top, rect.right-rect.left, 300))
img.save(r'D:\7tan\7tanAI\scripts\qq_395876_top.png')

eng = RapidOCR()
result, _ = eng(np.array(img))
print('=== 窗口顶部 OCR ===')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + rect.left
        cy = int((min(ys)+max(ys))/2) + rect.top
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
