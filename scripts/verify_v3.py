# -*- coding: utf-8 -*-
"""RapidOCR 验证 v3 粘贴结果"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()

for name, path, ox, oy in [
    ('输入框', r'D:\7tan\7tanAI\scripts\qq_input_v3.png', 850, 700),
]:
    img = Image.open(path).convert('RGB')
    result, _ = eng(np.array(img))
    print(f'=== {name} ({img.width}x{img.height}) ===')
    if result:
        for box, text, score in result:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            cx = int((min(xs)+max(xs))/2) + ox
            cy = int((min(ys)+max(ys))/2) + oy
            print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
    else:
        print('  无文字')
