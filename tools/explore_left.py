# -*- coding: utf-8 -*-
"""探索左栏顶部区域，找搜索框（点击后 OCR 对比变化）"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.2

hwnd = 657102
rect = win32gui.GetWindowRect(hwnd)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def snap_top():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    crop = img.crop((0, 0, w, 240))
    big = crop.resize((crop.width*3, crop.height*3), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

last = snap_top()
print("INITIAL:", last[:100])

candidates = [
    (0.2, 0.09), (0.2, 0.11), (0.25, 0.10), (0.15, 0.10), (0.18, 0.08),
    (0.22, 0.13), (0.18, 0.12), (0.28, 0.09), (0.1, 0.10), (0.12, 0.12),
    (0.25, 0.15), (0.15, 0.14),
]
for i, (rx, ry) in enumerate(candidates):
    cx, cy = x0 + int(w*rx), y0 + int(h*ry)
    pyautogui.click(cx, cy)
    time.sleep(1.6)
    t = snap_top()
    changed = (t != last)
    print(f"[{i}] ({rx},{ry})->({cx},{cy}) CHANGED={changed}")
    if changed:
        print("   NEW:", t[:150])
        img = Image.open(r'D:\7tan\7tanAI\tools\ocr_work\full1.png')
        last = t
        # 保存现场
        with mss.MSS() as sct:
            shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
        img2 = Image.frombytes('RGB', shot.size, shot.rgb)
        img2.save(rf'D:\7tan\7tanAI\tools\ocr_work\hit_{i}.png')
        print(f"   saved hit_{i}.png")
        break
    time.sleep(0.3)
print("DONE")
