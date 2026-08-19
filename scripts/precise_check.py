# -*- coding: utf-8 -*-
"""精确OCR当前QQ窗口底部和顶部，判断是否进入聊天模式"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()

for name, region, ox, oy in [
    ('底部', (480, 700, 1060, 140), 480, 700),
    ('顶部', (480, 200, 1060, 150), 480, 200),
]:
    img = pyautogui.screenshot(region=region)
    result, _ = eng(np.array(img))
    print(f'=== {name} ===')
    if result:
        for box, text, score in result:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            cx = int((min(xs)+max(xs))/2) + ox
            cy = int((min(ys)+max(ys))/2) + oy
            print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
    else:
        print('  无文字')
