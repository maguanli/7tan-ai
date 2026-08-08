# -*- coding: utf-8 -*-
"""RapidOCR 分析6张探测截图，找'a'出现在哪"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

eng = RapidOCR()

for i in range(6):
    path = rf'D:\7tan\7tanAI\scripts\qq_probe_{i}.png'
    img = Image.open(path).convert('RGB')
    result, _ = eng(np.array(img))
    texts = [f"({int((min(p[0] for p in b)+max(p[0] for p in b))/2)+480},{int((min(p[1] for p in b)+max(p[1] for p in b))/2)+700}) {t}" for b, t, s in (result or [])]
    # 过滤只显示含 a 或 发送 或明显文字
    interesting = [t for t in texts if 'a' in t.lower() or '发送' in t or 'A' in t]
    print(f'候选{i}: ' + (' | '.join(interesting) if interesting else '(无可疑文字)'))
