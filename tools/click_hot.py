# -*- coding: utf-8 -*-
"""点「文章」tab (612,165) → 找「最热」→ 点最热 → OCR 文章结果"""
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
        time.sleep(1.0)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

ensure_front()

# 1) 点「文章」tab
pyautogui.click(x0 + 612, y0 + 165)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("=== 点文章后 ===")
print("FULL:", text[:250])

# 2) 找「最热」位置并点击
hot_pos = None
for wx, wy, ww, wh, wt in words:
    if '最热' in wt:
        hot_pos = (wx + ww//2, wy + wh//2)
        print(f"找到「最热」: 窗口内 ({wx},{wy}) 绝对 ({x0+wx+ww//2},{y0+wy+wh//2})")
        break
if hot_pos:
    pyautogui.click(x0 + hot_pos[0], y0 + hot_pos[1])
    time.sleep(3.0)
    img2 = snap()
    img2.save(r'D:\7tan\7tanAI\tools\ocr_work\article_hot.png')
    words2, text2 = ocr_all(img2)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\article_hot.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words2:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text2)
    print("=== 点最热后 ===")
    print("FULL:", text2[:400])
else:
    print("未找到最热，保存当前页面")
    img.save(r'D:\7tan\7tanAI\tools\ocr_work\article_now.png')
