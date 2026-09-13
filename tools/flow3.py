# -*- coding: utf-8 -*-
"""自适应流程：打开搜一搜→文章→最热→列文章（全用OCR关键词定位）"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui, pyperclip
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

WX_HWND = 1509102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0
print("rect:", rect, "size:", w, "x", h)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

def find_and_click(words, kws, xmin=0, xmax=9999, ymin=0, ymax=9999, label=''):
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if xmin <= wx <= xmax and ymin <= wy <= ymax:
            for kw in kws:
                if kw in t:
                    cx, cy = x0 + wx + ww//2, y0 + wy + wh//2
                    print(f"  ✓ {label or kw}: ({wx},{wy}) -> 绝对({cx},{cy})")
                    return cx, cy
    print(f"  ✗ 未找到 {label or kws}")
    return None

# 1) 打开搜一搜
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("1. 搜一搜:", text[:120])

# 2) 关键词
if '游戏推荐' not in text:
    pyautogui.click(x0 + 300, y0 + 60)
    time.sleep(1.0)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.5)
    pyperclip.copy('游戏推荐')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.5)
    img = snap()
    words, text = ocr_all(img)
    print("2. 输入后:", text[:120])

# 3) 点「文章」tab
pos = find_and_click(words, ['文章'], xmin=400, xmax=1500, ymin=100, ymax=250, label='文章tab')
if pos:
    pyautogui.click(*pos)
    time.sleep(2.5)
    img = snap()
    words, text = ocr_all(img)
    print("3. 文章页:", text[:120])

# 4) 点「最热」
pos = find_and_click(words, ['最热'], xmin=400, xmax=1500, ymin=150, ymax=300, label='最热')
if pos:
    pyautogui.click(*pos)
    time.sleep(3.0)
    img = snap()
    img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_final.png')
    words, text = ocr_all(img)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_final.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text)
    print("4. 最热页:", text[:200])
    # 列出右侧文章标题（x>400, y>300）
    print("=== 文章列表 ===")
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 400 and wy >= 300 and len(t) >= 8:
            print(f"  ({wx},{wy}) {t}")
