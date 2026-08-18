# -*- coding: utf-8 -*-
"""验证：点击搜索框后 write('game') 是否生效；对比剪贴板粘贴"""
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

def ocr_all(img):
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

ensure_front()
pyautogui.click(x0+154, y0+58)
time.sleep(1.2)
pyautogui.write('game', interval=0.1)
time.sleep(1.0)
t1 = ocr_all(snap())
print("write('game') ->", t1[:100])

# 清空后粘贴
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('backspace')
time.sleep(0.5)
pyperclip.copy('hello')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)
t2 = ocr_all(snap())
print("paste('hello') ->", t2[:100])

# 再试一次粘贴（第二次）
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('backspace')
time.sleep(0.5)
pyperclip.copy('hello2')
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)
t3 = ocr_all(snap())
print("paste('hello2') ->", t3[:100])
