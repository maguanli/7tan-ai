# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from ocr_locate_click import recognize_lines

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\gzh_after_click.png")
print("size:", img.size)
lines = recognize_lines(img)
print("lines:", len(lines))
for text, x, y, w, h in lines[:50]:
    print(f"({x},{y},{w}x{h}) {text[:60]!r}")
