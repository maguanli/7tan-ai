# -*- coding: utf-8 -*-
"""检查截图内容：文件大小、平均颜色、是否全黑/全白"""
import sys
from pathlib import Path
from PIL import Image
import statistics

for p in sys.argv[1:]:
    path = Path(p)
    if not path.exists():
        print(f"{p}: NOT_EXISTS")
        continue
    img = Image.open(path).convert('RGB')
    small = img.resize((64, 64))
    pixels = list(small.getdata())
    avg_r = statistics.mean(p[0] for p in pixels)
    avg_g = statistics.mean(p[1] for p in pixels)
    avg_b = statistics.mean(p[2] for p in pixels)
    # 颜色多样性
    uniq = len(set(pixels))
    print(f"{p}: size={path.stat().st_size}B img={img.size} avgRGB=({avg_r:.0f},{avg_g:.0f},{avg_b:.0f}) uniq_colors(64x64)={uniq}")
