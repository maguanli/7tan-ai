# -*- coding: utf-8 -*-
"""点击顶部中央 → 输入「游戏推荐」→ 回车 → 截图验证是否进入搜索"""
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

def snap(fname):
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    img.save(fname)
    return img

def ocr_text(img):
    crop = img.crop((0, 0, w, 400))
    big = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

# 1) 关闭可能存在的菜单
pyautogui.click(x0 + int(w*0.85), y0 + int(h*0.18))
time.sleep(0.8)

# 2) 点击顶部中央（候选 y：0.07~0.11，x：0.5）
for ry in (0.07, 0.09, 0.11):
    cx, cy = x0 + int(w*0.5), y0 + int(h*ry)
    pyautogui.click(cx, cy)
    time.sleep(1.2)
    t = ocr_text(snap(r'D:\7tan\7tanAI\tools\ocr_work\pre_type.png'))
    print(f"click (0.5,{ry}) OCR:", t[:80])
    # 输入文字，看是否有光标反应
    pyautogui.write('game', interval=0.1)
    time.sleep(0.8)
    t2 = ocr_text(snap(r'D:\7tan\7tanAI\tools\ocr_work\typed.png'))
    print(f"   after type 'game':", t2[:80])
    if t2 != t:
        print(f"!!! 输入生效！位置 (0.5,{ry})")
        break
    # 清掉可能输入的字符
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.5)
print("END-EXPLORE")
