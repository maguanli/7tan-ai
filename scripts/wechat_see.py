# -*- coding: utf-8 -*-
"""wechat_see.py — 微信窗口专用视觉：定位窗口→区域截图→双引擎OCR→输出布局"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui
import mss

ROOT = r"D:\7tan\7tanAI"
SHOTS = os.path.join(ROOT, "data", "screenshots")
os.makedirs(SHOTS, exist_ok=True)

# 1. 找微信窗口
def find_wechat():
    wins = []
    def cb(h, out):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and ('微信' in t or 'Weixin' in t or 'WeChat' in t):
                out.append((h, t))
    win32gui.EnumWindows(cb, wins)
    return wins

wins = find_wechat()
if not wins:
    print("NO_WECHAT_WINDOW")
    sys.exit(1)
hwnd, title = wins[0]
rect = win32gui.GetWindowRect(hwnd)
print(f"窗口: {title} hwnd={hwnd} rect={rect}")

# 2. 区域截图
x0, y0, x1, y1 = rect
region = {"left": max(0, x0), "top": max(0, y0), "width": min(1920, x1) - max(0, x0), "height": min(1080, y1) - max(0, y0)}
with mss.mss() as sct:
    img = sct.grab(region)
    from PIL import Image
    pil = Image.frombytes("RGB", img.size, img.rgb)
    shot_path = os.path.join(SHOTS, "wechat_see.png")
    pil.save(shot_path)
print(f"已截图: {shot_path} {pil.size}")

# 3. RapidOCR 识别（中文准）
try:
    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()
    res, _ = eng(shot_path)
    print("===== RapidOCR =====")
    if res:
        for box, text, score in res:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            cx = int(sum(xs)/4) + x0; cy = int(sum(ys)/4) + y0
            print(f"({cx},{cy}) {text}")
    else:
        print("(无识别结果)")
except Exception as e:
    print(f"RapidOCR 失败: {e}")
