# -*- coding: utf-8 -*-
"""RapidOCR 识别窗口1443834顶部+左侧，确认窗口模式和是否有输入框"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image
import pyautogui
import ctypes
import time

user32 = ctypes.windll.user32
QQ_HWND = 1443834
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)

eng = RapidOCR()

# 顶部 300px
img_top = pyautogui.screenshot(region=(480, 200, 1060, 300))
img_top.save(r'D:\7tan\7tanAI\scripts\qq_top_300.png')
print('=== 顶部300px (y=200~500) ===')
result, _ = eng(np.array(img_top))
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 200
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')

# 左侧 400px 全高
img_left = pyautogui.screenshot(region=(480, 200, 400, 640))
img_left.save(r'D:\7tan\7tanAI\scripts\qq_left_400.png')
print('\n=== 左侧400px (x=480~880, y=200~840) ===')
result, _ = eng(np.array(img_left))
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 200
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
