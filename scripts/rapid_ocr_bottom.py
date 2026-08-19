# -*- coding: utf-8 -*-
"""用 RapidOCR 识别QQ窗口底部，输出带坐标的文字，定位发送按钮/输入框"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()

# 窗口底部 y=600~840
img = Image.open(r'D:\7tan\7tanAI\scripts\qq_bottom_area.png').convert('RGB')
# 底部区域对应绝对坐标 y=440~840，我们只看 y=600~840（相对 160~400）
crop = img.crop((0, 160, 1060, 400))
crop.save(r'D:\7tan\7tanAI\scripts\qq_bottom_crop.png')
print(f'裁剪区域: 1060x240 (绝对 y=600~840)')

arr = np.array(crop)
result, _ = eng(arr)
print(f'识别 {len(result) if result else 0} 行:')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        cx = int((min(xs) + max(xs)) / 2) + 480   # 加窗口x偏移
        cy = int((min(ys) + max(ys)) / 2) + 600   # 加绝对y偏移(600)
        print(f'  ({cx:4d},{cy:4d}) {text}  score={score:.2f}')
