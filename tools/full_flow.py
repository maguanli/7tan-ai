# -*- coding: utf-8 -*-
"""完整流程：打开搜一搜 → 确保关键词 → 文章tab → 最热 → 点开第一篇文章 → OCR全文"""
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

def find_word(words, keywords, xmin=0, xmax=9999, ymin=0, ymax=9999):
    """在 words 中找包含任一关键词的行，返回中心绝对坐标"""
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if xmin <= wx <= xmax and ymin <= wy <= ymax:
            for kw in keywords:
                if kw in t:
                    return (x0 + wx + ww//2, y0 + wy + wh//2), (wx, wy, t)
    return None, None

print("1. ensure_front:", ensure_front())
# 打开搜一搜
pyautogui.click(x0 + 80, y0 + 179)
time.sleep(2.5)
img = snap()
words, text = ocr_all(img)
print("2. 搜索页:", text[:120])
has_search_page = ('搜一搜' in text) or ('搜' in text and '游戏' in text)

# 如果搜索框没内容，输入关键词
if '游戏推荐' not in text:
    # 点击搜索输入框（窗口内 ~(120,60) 附近，或顶部）
    pyautogui.click(x0 + 250, y0 + 60)
    time.sleep(1.0)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.5)
    pyperclip.copy('游戏推荐')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.5)
    print("3. 已输入游戏推荐")
    img = snap()
    words, text = ocr_all(img)
    print("   输入后:", text[:120])

# 点「文章」tab
pos, info = find_word(words, ['文章'], xmin=500, xmax=700, ymin=140, ymax=200)
if pos:
    pyautogui.click(*pos)
    print(f"4. 点击文章tab {pos} ({info[2]})")
    time.sleep(2.5)
    img = snap()
    words, text = ocr_all(img)
    print("   文章页:", text[:120])
else:
    print("4. 未找到文章tab，当前:", text[:150])

# 点「最热」（在「最新最热已关注」行，「最热」= 第2项）
hot_pos, _ = find_word(words, ['最新最热', '最热'], xmin=520, xmax=800, ymin=190, ymax=240)
if hot_pos:
    # 若是「最新最热已关注」合并行，取第2个词中心（最热）
    cx, cy = hot_pos
    # 修正：合并行 146px/3 项，「最热」中心 = x + 48 + 24
    pyautogui.click(x0 + 675, y0 + 218)
    print("5. 点击最热 (675,218)")
    time.sleep(3.0)
    img = snap()
    words, text = ocr_all(img)
    print("   最热列表:", text[:150])
else:
    print("5. 未找到最热，当前:", text[:150])

# 找第一篇文章标题（x>540, y>250）
target = None
for wx, wy, ww, wh, wt in words:
    t = wt.replace(' ', '')
    if wx >= 540 and wy >= 250 and len(t) >= 10 and ('小游戏' in t or '游戏' in t):
        target = (wx + ww//2, wy + wh//2)
        print(f"6. 第一篇文章: ({wx},{wy}) {t} -> 绝对{target}")
        break
if target:
    pyautogui.click(x0 + target[0], y0 + target[1])
    time.sleep(4.5)
    img2 = snap()
    img2.save(r'D:\7tan\7tanAI\tools\ocr_work\article_final.png')
    words2, text2 = ocr_all(img2)
    with open(r'D:\7tan\7tanAI\tools\ocr_work\article_final.txt', 'w', encoding='utf-8') as f:
        for wx, wy, ww, wh, wt in words2:
            f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
        f.write("\nFULL:\n" + text2)
    print("=== 文章内容 ===")
    print(text2[:800])
