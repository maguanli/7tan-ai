# -*- coding: utf-8 -*-
"""严谨探索搜索框：确认前台→点击→输入测试→检测变化"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.25

WX_HWND = 657102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(0.8)
    return win32gui.GetForegroundWindow() == WX_HWND

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_top(img, top_h=320):
    crop = img.crop((0, 0, w, top_h))
    big = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

# 候选位置：x=列表栏/中部，y=顶部区域
candidates = [
    (0.16,0.09),(0.18,0.09),(0.22,0.09),(0.27,0.09),(0.32,0.09),
    (0.16,0.11),(0.2,0.11),(0.25,0.11),(0.3,0.11),(0.35,0.11),
    (0.2,0.13),(0.27,0.13),(0.33,0.13),
]
found = False
for i, (rx, ry) in enumerate(candidates):
    if not ensure_front():
        print(f"[{i}] 无法将微信置前，停止"); break
    cx, cy = x0 + int(w*rx), y0 + int(h*ry)
    pyautogui.click(cx, cy)
    time.sleep(1.2)
    before = ocr_top(snap())
    pyautogui.write('game', interval=0.08)
    time.sleep(1.0)
    after = ocr_top(snap())
    changed = (after != before)
    print(f"[{i}] ({rx},{ry})->({cx},{cy}) CHANGED={changed}")
    if changed:
        print("   BEFORE:", before[:120])
        print("   AFTER :", after[:120])
        snap().save(rf'D:\7tan\7tanAI\tools\ocr_work\sbhit_{i}.png')
        found = True
        break
    # 清理可能输入
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.4)
print("FOUND" if found else "NOT_FOUND")
