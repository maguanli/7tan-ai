# -*- coding: utf-8 -*-
"""在搜索框输入「游戏推荐」并回车，进入搜索结果页"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, win32con, mss
import pyautogui, pyperclip
import wechat_scan as ws

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.25

WX_HWND = 657102
rect = win32gui.GetWindowRect(WX_HWND)
x0, y0, x1, y1 = rect
w, h = x1-x0, y1-y0
SB = (x0 + 154, y0 + 58)  # 搜索框绝对坐标

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(0.8)
    return win32gui.GetForegroundWindow() == WX_HWND

def snap(fname):
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    img.save(fname)
    return img

def ocr_all(img, top_h=0):
    if top_h:
        img = img.crop((0, 0, w, top_h))
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

if not ensure_front():
    print("CANNOT_FRONT"); sys.exit(1)

# 1) 点击搜索框
pyautogui.click(*SB)
time.sleep(1.0)
# 2) 清空已输入的 game
pyautogui.hotkey('ctrl', 'a')
pyautogui.press('backspace')
time.sleep(0.6)
# 3) 粘贴「游戏推荐」
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.2)
t = ocr_all(snap(r'D:\7tan\7tanAI\tools\ocr_work\search_input.png'))
print("AFTER_PASTE:", t[:200])
# 4) 回车
pyautogui.press('enter')
time.sleep(3.0)
t2 = ocr_all(snap(r'D:\7tan\7tanAI\tools\ocr_work\search_result.png'))
print("AFTER_ENTER:", t2[:300])
