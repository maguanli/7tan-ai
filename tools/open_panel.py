# -*- coding: utf-8 -*-
"""打开搜索面板：点击触发按钮 (174,77) → 验证面板 → 输入"""
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

def ocr_all(img, top_h=0):
    if top_h:
        img = img.crop((0, 0, w, top_h))
    big = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    words, text = ws.ocr_words(big, scale=1.0)
    return text.replace(' ', '')

ensure_front()

# 候选触发按钮：窗口内 (174,77) 及附近
cands = [(174,77), (212,83), (174,70), (212,75), (160,80), (190,85)]
for i, (rx, ry) in enumerate(cands):
    cx, cy = x0 + rx, y0 + ry
    pyautogui.click(cx, cy)
    time.sleep(1.5)
    t = ocr_all(snap(), 500)
    # 面板特征：出现「搜索」或「历史」或输入框占位
    flag = ('搜索' in t) or ('最近' in t) or ('历史' in t)
    print(f"[{i}] click({rx},{ry})->({cx},{cy}) panel={flag} | {t[:80]}")
    if flag:
        print("   ✓ 面板打开！")
        snap().save(rf'D:\7tan\7tanAI\tools\ocr_work\panel_{i}.png')
        # 直接输入验证
        pyautogui.write('game', interval=0.1)
        time.sleep(1.2)
        t2 = ocr_all(snap(), 500)
        print("   AFTER write:", t2[:80])
        if 'game' in t2:
            print("   ✓ 输入生效！搜索面板输入框已定位")
        break
    time.sleep(0.4)
