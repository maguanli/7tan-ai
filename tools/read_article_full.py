# -*- coding: utf-8 -*-
"""滚动读取当前文章全文（每屏OCR保存）"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

WX_HWND = 657102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(1.2)
    return win32gui.GetForegroundWindow() == WX_HWND

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

ensure_front()
# 鼠标移到文章正文区域
pyautogui.moveTo(x0 + 800, y0 + 400)
time.sleep(0.5)

all_text = []
for i in range(8):
    img = snap()
    img.save(rf'D:\7tan\7tanAI\tools\ocr_work\art_page_{i}.png')
    words, text = ocr_all(img)
    all_text.append(text)
    print(f"===== 屏{i} (chars={len(text)}) =====")
    print(text[:350])
    pyautogui.scroll(-400)
    time.sleep(1.8)

# 保存全文
with open(r'D:\7tan\7tanAI\tools\ocr_work\article_full.txt', 'w', encoding='utf-8') as f:
    f.write("\n\n=====SCREEN-BREAK=====\n\n".join(all_text))
print("FULL SAVED: article_full.txt")
