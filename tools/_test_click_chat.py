# -*- coding: utf-8 -*-
"""测试点击微信聊天项是否有效果"""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.5)

def grab():
    with mss.mss() as sct:
        shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def diff_pct(a, b):
    pa, pb = a.load(), b.load()
    w, h = a.size
    diff = total = 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            total += 1
            if abs(pa[x,y][0]-pb[x,y][0]) + abs(pa[x,y][1]-pb[x,y][1]) + abs(pa[x,y][2]-pb[x,y][2]) > 30:
                diff += 1
    return diff / total * 100 if total else 0

img0 = grab()

# 点击聊天项"湛江政法"（相对窗口 x=126+7=133, y=119+6=125 → 绝对 484, 274）
# 先用更保险的位置：第一行聊天项文字中心 (484, 274)
for name, (cx, cy) in {
    "聊天项1(湛江政法)": (484, 274),
    "搜索框": (545, 205),
    "左侧栏顶部": (430, 200),
}.items():
    pyautogui.click(cx, cy)
    time.sleep(1.2)
    img = grab()
    d = diff_pct(img0, img)
    print(f"点击[{name}] ({cx},{cy}) → 全窗口变化 {d:.2f}%")
    if d > 2:
        img.save(r"D:\7tan\7tanAI\data\screenshots\click_" + name + ".png")
        print(f"  ✅ 有明显变化！已保存截图")
        break
    time.sleep(0.3)
