# -*- coding: utf-8 -*-
"""终极流程：搜一搜→文章→最热→找阅读量→打开10万+文章→读全文"""
import sys, io, time, re
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

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(1.0)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

def find_word(words, kw, xmin=0, xmax=99999, ymin=0, ymax=99999):
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if xmin <= wx <= xmax and ymin <= wy <= ymax and kw in t:
            return (x0 + wx + ww//2, y0 + wy + wh//2), (wx, wy, t)
    return None, None

ensure_front()
# 1) 打开搜一搜
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("1.搜一搜:", text[:80])

# 2) 点搜索框输入「游戏推荐」（搜索框在页面顶部中央附近 y~120）
pyautogui.click(x0 + 800, y0 + 120)
time.sleep(1.0)
pyautogui.hotkey('ctrl', 'a')
pyautogui.press('backspace')
time.sleep(0.5)
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)
img = snap()
words, text = ocr_all(img)
print("2.输入后:", text[:80])

# 3) 点「文章」tab（OCR定位，y 150~230）
pos, info = find_word(words, '文章', xmin=1400, xmax=1950, ymin=140, ymax=240)
if pos:
    pyautogui.click(*pos)
    time.sleep(3.0)
    img = snap()
    words, text = ocr_all(img)
    print("3.文章页:", text[:80])
else:
    print("3.未找到文章tab", text[:120])

# 4) 点「最热」（「最新最热已关注」行）
hot_info = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if '最新' in t and '最热' in t and wx > 1400:
        # 计算「最热」中心：第2项
        item_w = ww / 3
        hx = x0 + wx + int(item_w * 1.5)
        hy = y0 + wy + wh // 2
        hot_info = (hx, hy, t)
        print(f"4.找到最新最热行: ({wx},{wy}) {t} -> 最热({hx},{hy})")
        break
if hot_info:
    pyautogui.click(hot_info[0], hot_info[1])
    time.sleep(3.5)
    img = snap()
    img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_final2.png')
    words, text = ocr_all(img, scale=3.0)  # 放大3x识别小字阅读量
    with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_final2.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text)
    print("5.最热页标题:", [wt for wx, wy, ww, wh, wt in words if wx > 1400 and 40 < wy < 140])
    # 找阅读量行
    print("=== 阅读量 ===")
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if '阅读' in t and wy > 100:
            print(f"  ({wx},{wy}) {t}")
    # 找文章标题
    print("=== 标题 ===")
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 1400 and wy >= 200 and len(t) >= 10:
            print(f"  ({wx},{wy}) {t}")
else:
    print("4.未找到最热行", text[:150])
