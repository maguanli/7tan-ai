# -*- coding: utf-8 -*-
"""返回搜索结果页 → 文章 → 最热 → 打开新闻哥10万+文章"""
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
# 点返回（左上角〈，窗口内 ~(50,28)）
pyautogui.click(x0 + 50, y0 + 28)
time.sleep(2.0)
img = snap()
words, text = ocr_all(img)
print("返回后:", text[:150])

# 确保在搜索结果页：找「文章」tab 或重新打开搜索
if '搜一搜' not in text and '文章' not in text:
    # 打开搜一搜
    pyautogui.click(x0 + 80, y0 + 179)
    time.sleep(2.5)
    img = snap()
    words, text = ocr_all(img)
    print("重开搜索页:", text[:150])

# 点「文章」tab
for wx, wy, ww, wh, wt in words:
    if 500 <= wx <= 700 and 140 <= wy <= 200 and '文章' in wt.replace(' ', ''):
        pyautogui.click(x0 + wx + ww//2, y0 + wy + wh//2)
        print(f"点文章tab ({wx},{wy})")
        break
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("文章页:", text[:120])

# 点「最热」= 窗口内 (675,218)
pyautogui.click(x0 + 675, y0 + 218)
time.sleep(3.0)
img = snap()
words, text = ocr_all(img)
print("最热页:", text[:150])

# 找「6款超魔性」文章（新闻哥 10万+）
target = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if wx >= 540 and wy >= 250 and ('超魔性' in t or '6款' in t):
        target = (wx + ww//2, wy + wh//2)
        print(f"找到目标文章: ({wx},{wy}) {t} -> {target}")
        break
if not target:
    # 取第一篇文章
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 540 and wy >= 250 and len(t) >= 10:
            target = (wx + ww//2, wy + wh//2)
            print(f"用第一篇: ({wx},{wy}) {t}")
            break
if target:
    pyautogui.click(x0 + target[0], y0 + target[1])
    time.sleep(5.0)
    img2 = snap()
    img2.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_article.png')
    words2, text2 = ocr_all(img2)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_article.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words2:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text2)
    print("=== 文章全文 ===")
    print(text2[:1000])
