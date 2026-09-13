# -*- coding: utf-8 -*-
"""稳健版：点击搜索框 → 粘贴 → 验证联想面板出现；候选位置逐步尝试"""
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

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_words_all(img):
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return words, text.replace(' ', '')

ensure_front()

# 候选搜索框位置（窗口内相对坐标）
cands = [(154, 58), (150, 55), (160, 60), (140, 58), (170, 58), (154, 62), (154, 66), (200, 60)]
for i, (rx, ry) in enumerate(cands):
    cx, cy = x0 + rx, y0 + ry
    pyautogui.click(cx, cy)
    time.sleep(1.2)
    # 先删空
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.6)
    pyperclip.copy('游戏推荐')
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.5)
    img = snap()
    words, text = ocr_words_all(img)
    has_suggest = ('游戏推荐' in text) and ('公众号' not in text.split('游戏推荐')[0][:10] or True)
    # 检测联想面板：文本包含多个「游戏推荐」或「小程序/解压」等联想词
    suggest_cnt = text.count('游戏推荐')
    print(f"[{i}] click({rx},{ry}) -> 游戏推荐出现次数={suggest_cnt} | head={text[:60]}")
    if suggest_cnt >= 2:
        img.save(rf'D:\7tan\7tanAI\tools\ocr_work\suggest_{i}.png')
        print(f"   ✓ 联想面板出现！saved suggest_{i}.png")
        # 输出联想项坐标
        for wx, wy, ww, wh, wt in words:
            if '游戏' in wt or '搜索' in wt or '小程序' in wt or '解压' in wt:
                print(f"     abs=({x0+wx},{y0+wy}) rel=({wx},{wy}) | {wt}")
        break
    # 没出现就清空继续下一个位置
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.5)
