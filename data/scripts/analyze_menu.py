import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image, ImageChops

before = pyautogui.screenshot(region=(600, 300, 440, 480))
pyautogui.rightClick(850, 570)
time.sleep(0.6)
after = pyautogui.screenshot(region=(600, 300, 440, 480))
after.save(r"D:\7tan\7tanAI\data\screenshots\menu2.png")

diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
bbox = diff.getbbox()
print("menu bbox:", bbox, flush=True)
if not bbox:
    print("NO MENU", flush=True)
    sys.exit(0)

menu = after.crop(bbox)
menu.save(r"D:\7tan\7tanAI\data\screenshots\menu_crop.png")
gray = menu.convert("L")
w, h = gray.size
print("menu size:", w, h, flush=True)

# 背景色采样（左上角）
bg = gray.getpixel((3, 3))
print("bg gray:", bg, flush=True)
# 文字是深是浅？
if bg > 128:
    # 深色文字浅底：找暗像素行
    def is_text(p):
        return p < 100
else:
    # 浅色文字深底：找亮像素行
    def is_text(p):
        return p > 150

rows = []
for y in range(h):
    cnt = sum(1 for x in range(w) if is_text(gray.getpixel((x, y))))
    rows.append(cnt)

# 找文字行区间（连续行）
ranges = []
in_t = False
for y, c in enumerate(rows):
    if c >= 3 and not in_t:
        start = y
        in_t = True
    elif c < 3 and in_t:
        ranges.append((start, y - 1))
        in_t = False
if in_t:
    ranges.append((start, h - 1))

print("text row ranges (relative to menu):", ranges, flush=True)
for rs in ranges:
    mid = (rs[0] + rs[1]) // 2
    print("item center y (abs):", bbox[1] + mid, flush=True)
