# -*- coding: utf-8 -*-
"""探索点击：在窗口顶部候选位置点击，检测界面变化（OCR 对比）"""
import sys, ctypes, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.15

hwnd = 657102
rect = win32gui.GetWindowRect(hwnd)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def top_text(img):
    crop = img.crop((0, 0, w, 220))
    big = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

last = top_text(snap())
print("INITIAL TOP TEXT:", last[:120])

candidates = [
    (0.5, 0.05), (0.5, 0.06), (0.5, 0.07), (0.5, 0.08), (0.5, 0.09), (0.5, 0.10),
    (0.3, 0.07), (0.7, 0.07), (0.25, 0.08), (0.75, 0.08),
]
for i, (rx, ry) in enumerate(candidates):
    cx, cy = x0 + int(w*rx), y0 + int(h*ry)
    pyautogui.click(cx, cy)
    time.sleep(1.8)
    t = top_text(snap())
    changed = (t != last)
    print(f"[{i}] click ({rx},{ry}) -> ({cx},{cy}) CHANGED={changed}")
    if changed:
        print("   NEW TOP TEXT:", t[:150])
        last = t
        # 若变化可能已打开搜索，停下来人工判断
        img = snap()
        img.save(rf'D:\7tan\7tanAI\tools\ocr_work\explore_{i}.png')
        print(f"   saved explore_{i}.png")
        break
    time.sleep(0.5)
print("DONE")
