# -*- coding: utf-8 -*-
"""最后尝试：固定窗口968x645 → 退出页面 → 搜一搜 → 文章 → 最热 → 打开新闻哥文章"""
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
# 固定窗口尺寸
win32gui.SetWindowPos(WX_HWND, 0, 351, 149, 968, 645, win32con.SWP_NOZORDER)
time.sleep(1.0)
win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
win32gui.SetForegroundWindow(WX_HWND)
time.sleep(1.0)
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0
print("rect:", rect, "size:", w, "x", h)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

# 1) 退出当前页面（点左上角返回，最多5次）
for i in range(5):
    img = snap()
    words, text = ocr_all(img)
    found = False
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wy < 130 and t.startswith('<'):
            pyautogui.click(x0 + wx + ww//2, y0 + wy + wh//2)
            print(f"返回: ({wx},{wy}) {t}")
            time.sleep(2.0)
            found = True
            break
    if not found:
        break
img = snap()
words, text = ocr_all(img)
print("主界面:", text[:80])

# 2) 打开搜一搜
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("搜一搜:", text[:100])

# 3) 输入关键词：点顶部搜索框（窗口内 154,58 是之前验证过的位置）
pyautogui.click(x0 + 154, y0 + 58)
time.sleep(1.0)
pyautogui.hotkey('ctrl', 'a')
pyautogui.press('backspace')
time.sleep(0.5)
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)
img = snap()
words, text = ocr_all(img)
print("输入后:", text[:100])

# 4) 点「文章」tab（窗口内 612,165 附近）
pyautogui.click(x0 + 612, y0 + 165)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("文章页:", text[:100])

# 5) 点「最热」（窗口内 675,218）
pyautogui.click(x0 + 675, y0 + 218)
time.sleep(3.5)
img = snap()
img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_v6.png')
words, text = ocr_all(img, scale=3.0)
with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_v6.txt', 'w', encoding='utf-8') as f:
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\nFULL:\n" + text)
print("最热页:", text[:250])
print("=== 阅读量 ===")
for wx, wy, ww, wh, wt in words:
    if '阅读' in wt.replace(' ', '') and wy > 100:
        print(f"  ({wx},{wy}) {wt}")
print("=== 标题 ===")
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if wx >= 400 and wy >= 200 and len(t) >= 10:
        print(f"  ({wx},{wy}) {t}")
