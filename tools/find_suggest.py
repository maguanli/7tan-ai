# -*- coding: utf-8 -*-
"""获取搜索联想面板坐标，点击第一个「游戏推荐」结果项"""
import sys, io, time, json
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
SB = (x0 + 154, y0 + 58)

def ensure_front():
    if win32gui.GetForegroundWindow() != WX_HWND:
        win32gui.ShowWindow(WX_HWND, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(WX_HWND)
        time.sleep(0.8)

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_words_full(img):
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return words, text.replace(' ', '')

ensure_front()
pyautogui.click(*SB)
time.sleep(1.0)
pyautogui.hotkey('ctrl', 'a')
pyautogui.press('backspace')
time.sleep(0.6)
pyperclip.copy('游戏推荐')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)

img = snap()
words, text = ocr_words_full(img)
print("=== WORDS ===")
for wx, wy, ww, wh, wt in words:
    if '游戏' in wt or '推荐' in wt or '搜索' in wt:
        print(f"  abs=({x0+wx},{y0+wy}) rel=({wx},{wy}) size=({ww},{wh}) | {wt}")
print("FULL:", text[:200])

# 找第一个含「游戏推荐」的行（联想项，y > 80 表示在面板内）
targets = [wt for wx, wy, ww, wh, wt in words if '游戏推荐' in wt.replace(' ', '')]
print("TARGETS:", targets[:8])
