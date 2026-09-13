# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from ocr_locate_click import full_screen_image, recognize_lines

img = full_screen_image()
# 底部按钮区
crop = img.crop((300, 880, 1100, 1010))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
lines = recognize_lines(crop)
print("bottom buttons:")
for text, x, y, w, h in lines:
    print(f"  ({300+x//2},{880+y//2},{w//2}x{h//2}) {text!r}")

# 右上角关闭按钮区
crop2 = img.crop((800, 130, 1100, 260))
crop2 = crop2.resize((crop2.width * 2, crop2.height * 2), Image.LANCZOS)
lines2 = recognize_lines(crop2)
print("top-right area:")
for text, x, y, w, h in lines2:
    print(f"  ({800+x//2},{130+y//2},{w//2}x{h//2}) {text!r}")
