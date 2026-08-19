# -*- coding: utf-8 -*-
"""触发QQ窗口重绘：InvalidateRect + 尺寸微调，解决部分区域透明问题"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui

user32 = ctypes.windll.user32
QQ_HWND = 395876

# 1. InvalidateRect 强制重绘
user32.InvalidateRect(QQ_HWND, None, True)
user32.UpdateWindow(QQ_HWND)
time.sleep(1.0)
print('已 InvalidateRect + UpdateWindow')

# 2. 尺寸微调触发重绘（+1px 再恢复）
rect = wt.RECT()
user32.GetWindowRect(QQ_HWND, ctypes.byref(rect))
print(f'当前: ({rect.left},{rect.top},{rect.right},{rect.bottom})')
user32.SetWindowPos(QQ_HWND, 0, rect.left, rect.top,
                    rect.right-rect.left+1, rect.bottom-rect.top+1,
                    0x0004 | 0x0010)  # SWP_NOZORDER | SWP_SHOWWINDOW
time.sleep(0.5)
user32.SetWindowPos(QQ_HWND, 0, rect.left, rect.top,
                    rect.right-rect.left, rect.bottom-rect.top,
                    0x0004 | 0x0010)
time.sleep(1.0)
print('尺寸微调完成')

# 3. 重新置顶
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.8)
print(f'前台: {user32.GetForegroundWindow()}')

# 4. 截图验证底部区域
img = pyautogui.screenshot(region=(480, 640, 1060, 200))
img.save(r'D:\7tan\7tanAI\scripts\qq_redraw_bottom.png')
from PIL import Image
gray = img.convert('L')
dark = sum(1 for p in gray.getdata() if p < 128)
print(f'底部区域深色像素: {dark/(gray.width*gray.height)*100:.2f}%')
