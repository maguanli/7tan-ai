# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from ocr_locate_click import full_screen_image, recognize_lines, _norm

img = full_screen_image()
lines = recognize_lines(img)
print("total lines:", len(lines))
for text, x, y, w, h in lines:
    nt = _norm(text)
    # 宽松匹配：包含 40 或 才明白 或 人生最好
    if ("40" in nt or "才明白" in nt or "人生最好" in nt or "四个字" in nt or "大起" in nt):
        print(f"({x},{y},{w}x{h}) raw={text!r}")
        print(f"    norm={nt!r}  match40={'40岁才明白' in nt}")
