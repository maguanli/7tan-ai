# -*- coding: utf-8 -*-
"""点文章tab(1782,172) → 找最热 → 点最热 → 读文章列表"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

WX_HWND = 1509102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

# 1) 点「文章」tab
pyautogui.click(x0 + 1782, y0 + 172)
time.sleep(3.0)
img = snap()
words, text = ocr_all(img)
print("文章页:", text[:180])

# 2) 找「最热」
hot = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if '最热' in t and wx > 1400:
        hot = (wx + ww//2, wy + wh//2)
        print(f"最热: ({wx},{wy}) {t} -> ({x0+hot[0]},{y0+hot[1]})")
        break
if hot:
    pyautogui.click(x0 + hot[0], y0 + hot[1])
    time.sleep(3.5)
    img = snap()
    img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_v2.png')
    words, text = ocr_all(img)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_v2.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text)
    print("最热页:", text[:250])
    print("=== 文章列表（x>1400, y>250）===")
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 1400 and wy >= 250 and len(t) >= 8:
            print(f"  ({wx},{wy}) {t}")
else:
    print("未找到最热")
    for wx, wy, ww, wh, wt in words:
        if wx > 1400 and 150 < wy < 300:
            print(f"  tab区: ({wx},{wy}) {wt}")
