# -*- coding: utf-8 -*-
"""截取QQ窗口完整底部 (480,700,1060,140) 并用RapidOCR带坐标识别"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image
import psutil
from rapidocr_onnxruntime import RapidOCR
import numpy as np

user32 = ctypes.windll.user32

def find_qq_windows():
    wins = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def enum_cb(h, lp):
        if not user32.IsWindowVisible(h):
            return True
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        try:
            if psutil.Process(p.value).name().lower() != 'qq.exe':
                return True
        except Exception:
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls, 256)
        if not cls.value.startswith('Chrome_WidgetWin'):
            return True
        r = wt.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        w, hh = r.right - r.left, r.bottom - r.top
        if w > 300 and hh > 300:
            wins.append((h, r.left, r.top, w, hh))
        return True
    user32.EnumWindows(enum_cb, 0)
    return wins

wins = find_qq_windows()
print(f'QQ窗口: {wins}')
QQ_HWND = max(wins, key=lambda x: x[3]*x[4])[0]
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)
print(f'前台: {user32.GetForegroundWindow()}')

# 完整底部截图
img = pyautogui.screenshot(region=(480, 700, 1060, 140))
img.save(r'D:\7tan\7tanAI\scripts\qq_bottom_full.png')

eng = RapidOCR()
result, _ = eng(np.array(img))
print(f'识别 {len(result) if result else 0} 行 (绝对坐标):')
if result:
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        cx = int((min(xs)+max(xs))/2) + 480
        cy = int((min(ys)+max(ys))/2) + 700
        print(f'  ({cx:4d},{cy:4d}) {text} score={score:.2f}')

# 像素分析：y=770~830 区域深色分布（找输入框框线）
import numpy as np2
arr = np.array(img.convert('L'))
dark = arr < 128
print('\n=== y=770~840 深色像素按x分布 ===')
for x in range(0, 1060, 40):
    cnt = dark[70:140, x:x+40].sum()
    if cnt > 10:
        print(f'  x={480+x}-{480+x+40}: {cnt}')
