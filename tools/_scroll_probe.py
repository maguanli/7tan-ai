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
        out.append((360 + int(x/1.5), 230 + int(y/1.5), text[:40]))
    return out

print("=== 初始状态 ===")
for t in ocr_center():
    print(" ", t)

# 鼠标到编辑区
pyautogui.moveTo(600, 400, duration=0.3)
time.sleep(0.5)

for i in range(4):
    pyautogui.scroll(-700)
    time.sleep(1.2)
    print(f"=== 滚动 {i+1} 次后 ===")
    for t in ocr_center():
        print(" ", t)
