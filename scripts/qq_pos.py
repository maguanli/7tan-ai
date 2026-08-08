# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import pygetwindow as gw

user32 = ctypes.windll.user32

# 找标题为 'QQ' 的窗口
wins = gw.getWindowsWithTitle('QQ')
print('QQ窗口数:', len(wins))
for w in wins:
    try:
        print(f'  hwnd={w._hWnd} pos=({w.left},{w.top}) size={w.width}x{w.height} visible={w.visible} title={w.title!r}')
    except Exception as e:
        print('  err', e)

# 取最大的可见窗口作为主窗口
main = None
for w in wins:
    try:
        if w.visible and w.width > 200 and w.height > 200:
            if main is None or (w.width * w.height > main.width * main.height):
                main = w
    except Exception:
        pass

if main:
    print(f'\n主窗口: hwnd={main._hWnd} pos=({main.left},{main.top}) size={main.width}x{main.height}')
    # 保存几何信息
    with open('data/qq_win_pos.txt', 'w') as f:
        f.write(f'{main.left},{main.top},{main.width},{main.height}')
    print('已保存到 data/qq_win_pos.txt')
else:
    print('未找到可见的主窗口')
