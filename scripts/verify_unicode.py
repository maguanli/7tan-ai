# -*- coding: utf-8 -*-
"""RapidOCR 验证 Unicode 注入结果"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()
img = Image.open(r'D:\7tan\7tanAI\scripts\qq_unicode_test.png').convert('RGB')
result, _ = eng(np.array(img))
print(f'识别 {len(result) if result else 0} 行:')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 500
        cy = int((min(ys)+max(ys))/2) + 770
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')
else:
    print('  无文字')
