# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui
from PIL import Image
from ocr_locate_click import full_screen_image, recognize_lines

def ocr_body():
    img = full_screen_image()
    crop = img.crop((380, 250, 950, 730))
    crop = crop.resize((int(crop.width*1.6), int(crop.height*1.6)), Image.LANCZOS)
    lines = recognize_lines(crop)
    out = []
    for text, x, y, w, h in lines:
        out.append((380 + int(x/1.6), 250 + int(y/1.6), text[:44]))
    return out

for i in range(7):
    pyautogui.press("pagedown")
    time.sleep(1.3)
    print(f"===== PageDown x{i+1} =====")
    for t in ocr_body():
        print("  ", t)
