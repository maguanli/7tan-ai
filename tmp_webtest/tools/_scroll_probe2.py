# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui
from PIL import Image
from ocr_locate_click import full_screen_image, recognize_lines

def ocr_center():
    img = full_screen_image()
    crop = img.crop((360, 230, 950, 720))
    crop = crop.resize((int(crop.width*1.5), int(crop.height*1.5)), Image.LANCZOS)
    lines = recognize_lines(crop)
    out = []
    for text, x, y, w, h in lines:
        out.append((360 + int(x/1.5), 230 + int(y/1.5), text[:38]))
    return out

# 1. 单击正文聚焦
pyautogui.click(634, 340)
time.sleep(1)
print("clicked body")
for t in ocr_center()[:8]:
    print(" ", t)

# 2. 滚轮
pyautogui.scroll(-800)
time.sleep(1.5)
print("--- after wheel ---")
for t in ocr_center()[:8]:
    print(" ", t)

# 3. PageDown
pyautogui.press("pagedown")
time.sleep(1.5)
print("--- after PageDown ---")
for t in ocr_center()[:8]:
    print(" ", t)

# 4. 方向键下
pyautogui.press("down", presses=5)
time.sleep(1.5)
print("--- after down x5 ---")
for t in ocr_center()[:8]:
    print(" ", t)
