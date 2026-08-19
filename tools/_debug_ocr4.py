# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from ocr_locate_click import full_screen_image, recognize_lines

img = full_screen_image()
lines = recognize_lines(img)
print("total lines:", len(lines))
for text, x, y, w, h in lines:
    print(f"({x},{y},{w}x{h}) {text[:60]!r}")
