# -*- coding: utf-8 -*-
"""稳健版终极流程：退出所有页面→主界面→搜一搜→文章→最热→打开10万+文章"""
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
print("rect:", rect, "size:", w, "x", h)

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
            return (wx + ww//2, wy + wh//2), t
    return None, None

ensure_front()

# ---- 1) 退出所有页面，回到主界面 ----
for i in range(5):
    img = snap()
    words, text = ocr_all(img)
    # 判断是否在文章/公众号页：左侧顶部有「< xxx」返回
    is_page = False
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wy < 120 and t.startswith('<') and len(t) < 20:
            is_page = True
            print(f"  返回按钮: ({wx},{wy}) {t}")
            pyautogui.click(x0 + wx + ww//2, y0 + wy + wh//2)
            time.sleep(2.0)
            break
    if not is_page:
        print("已回到主界面")
        break
print("当前:", [wt for wx, wy, ww, wh, wt in words if wx > 400 and 40 < wy < 150][:5])

# ---- 2) 打开搜一搜 ----
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("搜一搜:", text[:100])

# ---- 3) 输入关键词（点搜索框） ----
pyautogui.click(x0 + 300, y0 + 120)
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

# ---- 4) 点「文章」tab ----
pos, info = find_word(words, '文章', xmin=400, xmax=1900, ymin=140, ymax=240)
if pos:
    pyautogui.click(x0 + pos[0], y0 + pos[1])
    print(f"点文章tab {pos} ({info})")
    time.sleep(3.0)
    img = snap()
    words, text = ocr_all(img)
    print("文章页:", text[:100])
else:
    print("未找到文章tab:", text[:150])

# ---- 5) 点「最热」 ----
hot = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if '最新' in t and '最热' in t and wx > 400:
        item_w = ww / 3
        hot = (wx + int(item_w * 1.5), wy + wh//2)
        print(f"最热行: ({wx},{wy}) {t} -> 最热中心 {hot}")
        break
if hot:
    pyautogui.click(x0 + hot[0], y0 + hot[1])
    time.sleep(3.5)
    img = snap()
    img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_v5.png')
    words, text = ocr_all(img, scale=3.0)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_v5.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text)
    print("最热页:", text[:200])
    print("=== 阅读量行 ===")
    for wx, wy, ww, wh, wt in words:
        if '阅读' in wt.replace(' ', '') and wy > 100:
            print(f"  ({wx},{wy}) {wt}")
    print("=== 文章标题 ===")
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if wx >= 400 and wy >= 200 and len(t) >= 10:
            print(f"  ({wx},{wy}) {t}")
else:
    print("未找到最热:", text[:200])
