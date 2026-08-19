# -*- coding: utf-8 -*-
"""截图当前屏幕 + 列出所有QQ窗口的位置状态"""
import mss
import pygetwindow as gw
import time

# 1. 列出所有 QQ 相关窗口
print("===== QQ 窗口列表 =====")
qq_wins = [w for w in gw.getAllWindows() if 'QQ' in w.title or w._hWnd and True]
for w in gw.getAllWindows():
    if w.title and ('QQ' in w.title):
        print(f"标题: {w.title!r} | 可见: {w.visible} | 最小化: {w.isMinimized} | 位置: ({w.left},{w.top}) 尺寸: {w.width}x{w.height}")

# 2. 全屏截图
with mss.mss() as sct:
    monitor = sct.monitors[0]  # 所有屏幕
    img = sct.grab(monitor)
    from PIL import Image
    pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
    pil_img.save(r"scripts\desktop_screenshot.png")
    print(f"\n已保存桌面截图: scripts/desktop_screenshot.png 尺寸: {pil_img.size}")
