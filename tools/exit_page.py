# -*- coding: utf-8 -*-
"""退出公众号主页：Esc + 点返回按钮 多组合"""
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

def snap():
    with mss.MSS() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    return Image.frombytes('RGB', shot.size, shot.rgb)

def ocr_all(img, scale=2.0):
    big = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=scale)
    return words, text.replace(' ', '')

def try_actions(actions):
    for name, fn in actions:
        fn()
        time.sleep(1.8)
        img = snap()
        words, text = ocr_all(img)
        print(f"[{name}] {text[:80]}")
        if '公众号' not in text[:20] or len(text) > 30:
            print(f"  -> 界面已变！saved")
            img.save(rf'D:\7tan\7tanAI\tools\ocr_work\exit_{name}.png')
            return text
    return None

try_actions([
    ('esc', lambda: pyautogui.press('esc')),
    ('back1', lambda: pyautogui.click(x0+94, y0+48)),
    ('back2', lambda: pyautogui.click(x0+60, y0+50)),
    ('back3', lambda: pyautogui.click(x0+80, y0+55)),
    ('top-left', lambda: pyautogui.click(x0+30, y0+30)),
    ('double-back', lambda: (pyautogui.click(x0+94, y0+48), pyautogui.click(x0+94, y0+48))),
])
