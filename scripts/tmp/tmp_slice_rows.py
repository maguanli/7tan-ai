# -*- coding: utf-8 -*-
"""把微信左侧列表切成横条，逐条保存，用于精确识别每行内容"""
from PIL import ImageGrab, Image
import os

out_dir = r"D:\7tan\7tanAI\data\screenshots\rows"
os.makedirs(out_dir, exist_ok=True)

# 列表区域 x=300-620, y=140-860
# 每 54px 一条（微信行高约54px），从 y=140 开始，切 13 条
for i in range(13):
    y0 = 140 + i * 54
    y1 = min(y0 + 54, 860)
    if y0 >= 860:
        break
    img = ImageGrab.grab(bbox=(300, y0, 620, y1))
    w, h = img.size
    img_big = img.resize((w * 3, h * 3), Image.LANCZOS)
    img_big.save(os.path.join(out_dir, f"row_{i:02d}_y{y0}-{y1}.png"))
    print(f"row_{i:02d}: y={y0}-{y1} saved")
