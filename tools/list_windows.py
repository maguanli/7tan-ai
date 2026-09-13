# -*- coding: utf-8 -*-
"""枚举所有可见窗口（标题+类名+rect），查找微信窗口真实名称"""
import ctypes, win32gui
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

rows = []
def cb(hwnd, _):
    if not win32gui.IsWindowVisible(hwnd):
        return
    title = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    try:
        rect = win32gui.GetWindowRect(hwnd)
    except Exception:
        rect = (0,0,0,0)
    w, h = rect[2]-rect[0], rect[3]-rect[1]
    if w <= 0 or h <= 0:
        return
    rows.append((hwnd, title, cls, w, h))

win32gui.EnumWindows(cb, None)
rows.sort(key=lambda r: r[3]*r[4], reverse=True)
print(f"TOTAL_VISIBLE={len(rows)}")
for hwnd, title, cls, w, h in rows[:60]:
    print(f"{hwnd} | {title[:50]!r} | {cls[:40]} | {w}x{h}")
