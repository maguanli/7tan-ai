# -*- coding: utf-8 -*-
"""把光标定位到「这还没完」，截图，并按像素判断图/文/空 带。"""
import os
import sys
import time

sys.path.insert(0, r"D:\7tan\7tanAI")
import _sohu_tool as T  # noqa

import pyautogui
import win32gui
from PIL import Image

T.focus()
pyautogui.hotkey("ctrl", "f")
time.sleep(1.0)
pyautogui.hotkey("ctrl", "a")
time.sleep(0.3)
pyautogui.press("delete")
time.sleep(0.3)
T.set_clip("text", "这还没完")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "v")
time.sleep(1.5)
pyautogui.press("enter")
time.sleep(1.5)
pyautogui.press("escape")
time.sleep(1.0)

# 取搜狐窗口范围
ws = T.find_windows("搜狐号")
l, t, r, b = win32gui.GetWindowRect(ws[0][0])
print("win:", l, t, r, b)
shot = pyautogui.screenshot(region=(l, t, r - l, b - t))
p = r"D:\7tan\7tanAI\data\screenshots\_sohu_look.png"
shot.save(p)
print("shot:", p, shot.size)

im = shot.convert("RGB")
W, H = im.size
px = im.load()
x0, x1 = 40, min(W, 950)
bands = []
cur = None
for y in range(0, H):
    non = col = 0
    for x in range(x0, x1, 2):
        r_, g_, b_ = px[x, y]
        if min(r_, g_, b_) < 235:
            non += 1
        if max(r_, g_, b_) - min(r_, g_, b_) > 40:
            col += 1
    n = (x1 - x0) // 2
    fn, fc = non / n, col / n
    if fc > 0.25:
        k = "PHOTO"
    elif fn > 0.015:
        k = "TEXT"
    else:
        k = "BLANK"
    if cur is None or cur[0] != k:
        if cur:
            bands.append(cur)
        cur = [k, y, y, 0]
    cur[2] = y
    cur[3] = max(cur[3], fn)
if cur:
    bands.append(cur)
for k, y1, y2, mx in bands:
    if y2 - y1 < 3 and k == "BLANK":
        continue
    print("  %-6s y=%4d..%4d  h=%3d  maxNonWhite=%.2f" % (k, y1, y2, y2 - y1 + 1, mx))
