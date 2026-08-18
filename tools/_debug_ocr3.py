# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from ocr_locate_click import full_screen_image, recognize_lines

img = full_screen_image()
lines = recognize_lines(img)
print("total lines:", len(lines))
for text, x, y, w, h in lines:
    if any(k in text for k in ["大起", "大落", "40", "才明白", "人生最好", "四个字", "草稿箱", "更新于", "21", "44"]):
        print(f"({x},{y},{w}x{h}) {text!r}")
