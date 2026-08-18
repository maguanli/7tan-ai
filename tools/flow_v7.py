# -*- coding: utf-8 -*-
"""调试版流程：详细坐标打印 + 逐步确认"""
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
print("rect:", rect)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

def dump(words, ymin, ymax, xmin=0, label=''):
    print(f"--- {label} (y {ymin}~{ymax}) ---")
    for wx, wy, ww, wh, wt in words:
        if xmin <= wx and ymin <= wy <= ymax:
            print(f"  ({wx},{wy}) {wt}")

# 1) 点击左侧搜索入口
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("STEP1 全文本:", text[:120])
dump(words, 40, 260, 300, "STEP1 右侧区域")

# 2) 输入关键词：点搜索框（看OCR的搜索框在哪）
# 搜索框通常在顶部中央（x 300~500, y 90~140）
pyautogui.click(x0 + 400, y0 + 110)
time.sleep(1.0)
pyautogui.hotkey('ctrl', 'a')
pyautogui.press('backspace')
time.sleep(0.5)
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)
img = snap()
words, text = ocr_all(img)
print("STEP2 全文本:", text[:150])
dump(words, 40, 260, 300, "STEP2 右侧区域")
