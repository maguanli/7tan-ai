# -*- coding: utf-8 -*-
"""完整稳定流程（微信已置顶）：返回→搜一搜→文章→最热→打开新闻哥10万+文章→读全文"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui, pyperclip
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
    return win32gui.GetForegroundWindow() == WX_HWND

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

print("front:", ensure_front())
# 1) 点返回按钮 (94,48)
pyautogui.click(x0 + 94, y0 + 48)
time.sleep(2.0)
img = snap()
words, text = ocr_all(img)
print("1.返回后:", text[:100])

# 2) 打开搜一搜
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("2.搜一搜:", text[:120])

# 3) 确保关键词「游戏推荐」
if '游戏推荐' not in text:
    pyautogui.click(x0 + 250, y0 + 60)
    time.sleep(1.0)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.5)
    pyperclip.copy('游戏推荐')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.5)
    print("3.已输入关键词")
    img = snap()
    words, text = ocr_all(img)
    print("   :", text[:120])

# 4) 点「文章」tab（窗口内 612,165）
pyautogui.click(x0 + 612, y0 + 165)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("4.文章页:", text[:120])

# 5) 点「最热」（窗口内 675,218）
pyautogui.click(x0 + 675, y0 + 218)
time.sleep(3.0)
img = snap()
words, text = ocr_all(img)
print("5.最热:", text[:150])

# 6) 找新闻哥文章「6款超魔性」
target = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if wx >= 540 and wy >= 250 and ('超魔性' in t):
        target = (wx + ww//2, wy + wh//2)
        print(f"6.新闻哥文章: ({wx},{wy}) {t}")
        break
if not target:
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 540 and wy >= 250 and len(t) >= 10 and '小游戏' in t:
            target = (wx + ww//2, wy + wh//2)
            print(f"6.替代第一篇: ({wx},{wy}) {t}")
            break
if target:
    pyautogui.click(x0 + target[0], y0 + target[1])
    time.sleep(5.0)
    img2 = snap()
    img2.save(r'D:\7tan\7tanAI\tools\ocr_work\news_article.png')
    words2, text2 = ocr_all(img2)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\news_article.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words2:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text2)
    print("=== 打开文章 ===")
    print(text2[:500])
