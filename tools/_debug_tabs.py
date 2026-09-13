# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from ocr_locate_click import full_screen_image, recognize_lines

img = full_screen_image()
crop = img.crop((200, 15, 700, 130))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
lines = recognize_lines(crop)
for text, x, y, w, h in lines:
    print(f"({200+x//2},{15+y//2},{w//2}x{h//2}) {text!r}")
