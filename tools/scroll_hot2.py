# -*- coding: utf-8 -*-
"""滚动最热文章列表，收集标题+公众号+阅读量"""
import sys, io, time, re
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

# 鼠标移到右侧列表
pyautogui.moveTo(x0 + 1700, y0 + 500)
time.sleep(0.5)

lines_all = []
for i in range(8):
    img = snap()
    img.save(rf'D:\7tan\7tanAI\tools\ocr_work\hotlist_{i}.png')
    words, text = ocr_all(img)
    lines_all.append((i, words))
    print(f"===== 屏{i} =====")
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 1400 and wy >= 260:
            # 标题（长文本）或阅读量或公众号
            if ('阅读' in t) or (len(t) >= 12) or ('/' in t and re.search(r'20\d\d', t)):
                print(f"  ({wx},{wy}) {t}")
    pyautogui.scroll(-500)
    time.sleep(2.0)
print("DONE")
