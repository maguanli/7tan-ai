# -*- coding: utf-8 -*-
"""把微信窗口置顶并激活，确认焦点"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pyautogui

user32 = ctypes.windll.user32
HWND = 329388
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

# 1. 显示并置顶
user32.ShowWindow(HWND, 9)  # SW_RESTORE
time.sleep(0.3)
user32.SetWindowPos(HWND, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
time.sleep(0.5)
# 取消置顶但保持前台
user32.SetWindowPos(HWND, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.3)

# 2. 点击微信窗口标题栏位置（窗口顶部），确保激活
# 微信窗口 rect: (50,100,766x514)
win_left, win_top = 50, 100
# 标题栏在窗口顶部中间
pyautogui.click(win_left + 383, win_top + 20)
time.sleep(1.0)

# 3. 检查前台窗口
fg = user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg, buf, 256)
print(f'前台窗口: hwnd={fg} title={buf.value!r}')

# 4. 再次点击标题栏并 Ctrl+F
pyautogui.click(win_left + 383, win_top + 20)
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'f')
time.sleep(1.2)
print('OK: 已按 Ctrl+F')

# 5. 粘贴搜索词
import pyperclip
pyperclip.copy('7坛游戏社区')
pyautogui.hotkey('ctrl', 'v')
time.sleep(2.0)
print('OK: 已粘贴搜索词')

# 6. 再检查前台窗口
fg2 = user32.GetForegroundWindow()
user32.GetWindowTextW(fg2, buf, 256)
print(f'操作后前台窗口: hwnd={fg2} title={buf.value!r}')
