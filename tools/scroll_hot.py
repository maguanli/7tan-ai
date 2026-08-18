# -*- coding: utf-8 -*-
"""滚动「最热」文章列表，收集所有文章标题+阅读量"""
import sys, io, time, re
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

all_articles = []  # (标题, 公众号, 时间, 阅读量)
seen_keys = set()

def parse_words(words):
    """从 words 中提取文章条目：标题行(x>540, 字高大)、摘要、公众号、阅读量"""
    items = []
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        # 右侧结果区 x>540
        if wx < 540:
            continue
        items.append((wx, wy, t))
    return items

def collect(words):
    """识别标题（y 与摘要分开），阅读量标记"""
    # 找「阅读」行
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if '阅读' in t and wy > 200:
            print(f"  [阅读量] ({wx},{wy}) {t}")
    # 找标题（在 x>540 区域、y>250、字数>8、非摘要行）
    # 简化：打印 x>540 的所有行
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 540 and wy >= 250 and len(t) >= 6:
            key = (wy // 50, t[:20])
            if key not in seen_keys:
                seen_keys.add(key)
                print(f"  [{wy}] {t}")

for round_i in range(6):
    img = snap()
    img.save(rf'D:\7tan\7tanAI\tools\ocr_work\hot_scroll_{round_i}.png')
    words, text = ocr_all(img)
    print(f"===== 第{round_i}屏 =====")
    collect(words)
    # 滚动（鼠标移到右侧结果区再滚）
    pyautogui.moveTo(x0 + 850, y0 + 500)
    time.sleep(0.4)
    pyautogui.scroll(-400)
    time.sleep(2.0)
print("DONE")
