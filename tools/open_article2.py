# -*- coding: utf-8 -*-
"""恢复微信前台 → 滚回顶部 → 点击10万+文章 → 读全文（每步验证）"""
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
    fg = win32gui.GetForegroundWindow()
    if fg != WX_HWND:
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

print("ensure_front:", ensure_front())
# 点击微信窗口标题栏空白处确保焦点
pyautogui.click(x0 + 500, y0 + 30)
time.sleep(0.8)

# 滚回顶部
pyautogui.moveTo(x0 + 850, y0 + 400)
time.sleep(0.5)
for _ in range(10):
    pyautogui.scroll(500)
    time.sleep(0.4)
time.sleep(2.0)

img = snap()
words, text = ocr_all(img)
print("TOP SCREEN:", text[:150])
if '7Tan' in text or 'AI工作台' in text:
    print("!! 还是7Tan界面，重试 restore")
    ensure_front()
    time.sleep(1)
    img = snap()
    words, text = ocr_all(img)
    print("RETRY TOP SCREEN:", text[:150])

target = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if ('超魔性' in t) or ('6款' in t and '小游戏' in t):
        target = (wx + ww//2, wy + wh//2)
        print(f"找到标题: ({wx},{wy}) -> 绝对({x0+wx+ww//2},{y0+wy+wh//2}) | {wt}")
        break
if target:
    pyautogui.click(x0 + target[0], y0 + target[1])
    time.sleep(4.5)
    img2 = snap()
    img2.save(r'D:\7tan\7tanAI\tools\ocr_work\article_open2.png')
    words2, text2 = ocr_all(img2)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\article_open2.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words2:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text2)
    print("=== 打开文章后 ===")
    print(text2[:700])
else:
    print("未找到文章标题，当前屏:", text[:200])
