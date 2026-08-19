# -*- coding: utf-8 -*-
"""RapidOCR 识别之前粘贴后的输入框截图 qq_input_after_paste2.png"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()

for name, path, ox, oy in [
    ('粘贴后输入框', r'D:\7tan\7tanAI\scripts\qq_input_after_paste2.png', 850, 700),
    ('窗口底部', r'D:\7tan\7tanAI\scripts\qq_bottom_area.png', 480, 440),
]:
    img = Image.open(path).convert('RGB')
    arr = np.array(img)
    result, _ = eng(arr)
    print(f'=== {name} ({img.width}x{img.height}) 识别 {len(result) if result else 0} 行 ===')
    if result:
        for box, text, score in result:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            cx = int((min(xs) + max(xs)) / 2) + ox
            cy = int((min(ys) + max(ys)) / 2) + oy
            print(f'  ({cx:4d},{cy:4d}) {text}  score={score:.2f}')
