# -*- coding: utf-8 -*-
"""RapidOCR 验证 qq_final_input4.png 输入框内容"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()

for name, path, ox, oy in [
    ('输入框', r'D:\7tan\7tanAI\scripts\qq_final_input4.png', 500, 770),
    ('全窗口', r'D:\7tan\7tanAI\scripts\qq_final_win4.png', 480, 200),
]:
    img = Image.open(path).convert('RGB')
    result, _ = eng(np.array(img))
    print(f'=== {name} ({img.width}x{img.height}) 识别 {len(result) if result else 0} 行 ===')
    if result:
        for box, text, score in result:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            cx = int((min(xs)+max(xs))/2) + ox
            cy = int((min(ys)+max(ys))/2) + oy
            print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
    else:
        print('  无文字')
