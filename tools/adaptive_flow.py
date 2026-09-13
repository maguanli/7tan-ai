# -*- coding: utf-8 -*-
"""自适应循环：OCR实时定位「文章」tab→点击→验证→定位「最热」→点击→读列表"""
import sys, io, time
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

def find_word(words, kw, xmin=0, xmax=99999, ymin=0, ymax=99999, exclude=None):
    for wx, wy, ww, wh, wt in words:
        t = wt.replace(' ', '')
        if xmin <= wx <= xmax and ymin <= wy <= ymax and kw in t:
            if exclude and any(e in t for e in exclude):
                continue
            return (x0 + wx + ww//2, y0 + wy + wh//2), (wx, wy, ww, t)
    return None, None

ensure_front()

# 循环定位并点击「文章」tab（y 140~210 区域，x>1400），排除「视频文章」合并词
for attempt in range(6):
    img = snap()
    words, text = ocr_all(img)
    print(f"[{attempt}] 标题:", [wt for wx, wy, ww, wh, wt in words if wx > 1400 and 40 < wy < 140][:3])
    pos, info = find_word(words, '文章', xmin=1400, xmax=1950, ymin=130, ymax=230, exclude=['视频'])
    if pos:
        print(f"  点文章tab: {info}")
        pyautogui.click(*pos)
        time.sleep(3.0)
        img = snap()
        words, text = ocr_all(img)
        # 验证是否进入文章页：标题含「文章·搜一搜」或出现「最新最热/最热」
        if '搜一搜' in text and ('文章' in text):
            print("  ✓ 疑似进入文章页")
        # 找「最热」
        hot_pos, hot_info = find_word(words, '最热', xmin=1400, xmax=1950, ymin=150, ymax=300)
        if hot_pos:
            print(f"  ★ 找到最热: {hot_info}")
            pyautogui.click(*hot_pos)
            time.sleep(3.5)
            img = snap()
            img.save(r'D:\7tan\7tanAI\tools\ocr_work\hot_v3.png')
            words, text = ocr_all(img)
            with open(r'D:\7tan\7tanAI\tools\ocr_work\hot_v3.txt', 'w', encoding='utf-8') as f:
                for wx, wy, ww, wh, wt in words:
                    f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
                f.write("\nFULL:\n" + text)
            print("最热页:", text[:250])
            print("=== 文章列表 ===")
            for wx, wy, ww, wh, wt in words:
                t = wt.replace(' ', '')
                if wx >= 1400 and wy >= 260 and len(t) >= 8:
                    print(f"  ({wx},{wy}) {t}")
            break
    time.sleep(1.0)
