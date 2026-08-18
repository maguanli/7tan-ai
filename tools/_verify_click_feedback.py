# -*- coding: utf-8 -*-
"""验证点击搜索框是否有视觉反馈 + 键盘输入测试"""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.5)

def grab(box):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def diff_pct(a, b):
    if a.size != b.size:
        return 999
    pa, pb = a.load(), b.load()
    w, h = a.size
    diff = 0
    total = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            total += 1
            if abs(pa[x,y][0]-pb[x,y][0]) + abs(pa[x,y][1]-pb[x,y][1]) + abs(pa[x,y][2]-pb[x,y][2]) > 30:
                diff += 1
    return diff / total * 100 if total else 0

# 搜索框区域
BOX = (411, 179, 260, 85)  # x=411 y=179 w=260 h=85（绝对坐标）

img_before = grab(BOX)
img_before.save(r"D:\7tan\7tanAI\data\screenshots\box_before.png")

# 点击搜索框中心
pyautogui.click(545, 205)
time.sleep(0.8)
img_after_click = grab(BOX)
img_after_click.save(r"D:\7tan\7tanAI\data\screenshots\box_after_click.png")
d1 = diff_pct(img_before, img_after_click)
print(f"点击后变化: {d1:.2f}%")

# 鼠标位置验证
print(f"鼠标位置: {pyautogui.position()}")

# 键盘输入 ASCII 测试
pyautogui.typewrite("abc", interval=0.2)
time.sleep(0.8)
img_after_type = grab(BOX)
img_after_type.save(r"D:\7tan\7tanAI\data\screenshots\box_after_type.png")
d2 = diff_pct(img_after_click, img_after_type)
print(f"输入abc后变化: {d2:.2f}%")

# 再点一次并检查是否弹出搜索建议面板（整个窗口 diff）
img_full_before = grab((351, 149, 968, 645))
pyautogui.click(545, 205)
time.sleep(1.5)
img_full_after = grab((351, 149, 968, 645))
d3 = diff_pct(img_full_before, img_full_after)
print(f"再次点击后全窗口变化: {d3:.2f}%")
if d3 > 1:
    img_full_after.save(r"D:\7tan\7tanAI\data\screenshots\after_search_panel.png")
    print("  → 界面有变化！可能弹出了搜索面板")
else:
    print("  → 界面无变化")
