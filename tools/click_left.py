# -*- coding: utf-8 -*-
"""点击左侧窄栏 (39,179) 附近 → write 验证搜索面板"""
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
cands = [(39,179), (39,150), (39,200), (39,230), (60,179), (80,179), (100,179), (30,179)]
for i, (rx, ry) in enumerate(cands):
    cx, cy = x0 + rx, y0 + ry
    pyautogui.click(cx, cy)
    time.sleep(1.3)
    pyautogui.write('game', interval=0.08)
    time.sleep(1.2)
    t = ocr_all(snap())
    found = ('game' in t)
    print(f"[{i}] click({rx},{ry})->({cx},{cy}) game_in_screen={found} | {t[:70]}")
    if found:
        print("   ✓✓ 搜索输入框命中！")
        snap().save(rf'D:\7tan\7tanAI\tools\ocr_work\panel_hit_{i}.png')
        # 清空 game
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        break
    # 清理
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.4)
