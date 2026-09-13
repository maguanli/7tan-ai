# -*- coding: utf-8 -*-
import sys, io
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from ocr_locate_click import recognize_lines

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\ocr_full.png")
# 裁剪中间 WebView 区域放大
crop = img.crop((280, 100, 1100, 1050))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
lines = recognize_lines(crop)
print("lines:", len(lines))
for text, x, y, w, h in lines:
    # 还原到原图坐标
    print(f"({280+x//2},{100+y//2},{w//2}x{h//2}) {text[:60]!r}")
