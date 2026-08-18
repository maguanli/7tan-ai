# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from ocr_locate_click import full_screen_image, recognize_lines, find_target

print("argv:", sys.argv)
img = full_screen_image()
lines = recognize_lines(img)

hit1 = find_target(lines, "才明白")
print("hardcode [才明白] ->", hit1)

if len(sys.argv) > 1:
    hit2 = find_target(lines, sys.argv[1])
    print(f"argv[{sys.argv[1]!r}] ->", hit2)
    print("argv repr bytes:", sys.argv[1].encode("unicode_escape"))
