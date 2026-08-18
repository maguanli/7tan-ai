# -*- coding: utf-8 -*-
"""点击列表栏顶部候选位置 → 输入 'game' → 检测输入是否生效（找搜索框）"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.25

hwnd = 657102
rect = win32gui.GetWindowRect(hwnd)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    return img

def ocr_top(img):
    crop = img.crop((0, 0, w, 320))
    big = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

# 候选：列表栏顶部区域（x 比例 0.13~0.3，y 比例 0.08~0.14）
candidates = [(0.15,0.09),(0.2,0.10),(0.25,0.11),(0.15,0.12),(0.2,0.13),(0.3,0.12),(0.25,0.08),(0.13,0.10)]
found = False
for i, (rx, ry) in enumerate(candidates):
    cx, cy = x0 + int(w*rx), y0 + int(h*ry)
    pyautogui.click(cx, cy)
    time.sleep(1.2)
    before = ocr_top(snap())
    pyautogui.write('game', interval=0.1)
    time.sleep(1.0)
    after = ocr_top(snap())
    changed = (after != before)
    print(f"[{i}] click({rx},{ry})->({cx},{cy}) type-test CHANGED={changed}")
    if changed:
        print("   BEFORE:", before[:100])
        print("   AFTER :", after[:100])
        found = True
        snap().save(rf'D:\7tan\7tanAI\tools\ocr_work\searchbox_{i}.png')
        print("   saved searchbox_{i}.png")
        break
    # 清理可能的输入
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.4)
if not found:
    print("NOT_FOUND - 需要另找搜索入口")
