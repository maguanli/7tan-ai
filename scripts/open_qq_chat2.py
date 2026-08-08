# -*- coding: utf-8 -*-
"""双击QQ会话列表中的7723群条目 (650,697) 打开聊天窗口"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import psutil

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
QQ_HWND = max(wins, key=lambda x: x[3]*x[4])[0] if wins else None
if not QQ_HWND:
    print('无QQ窗口')
    sys.exit(1)
print(f'QQ窗口: {QQ_HWND}')
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)

# 先点击选中会话列表中的7723群条目，再双击
print('单击选中 (650, 697)...')
pyautogui.click(650, 697)
time.sleep(0.8)
print('双击 (650, 697)...')
pyautogui.doubleClick(650, 697)
time.sleep(1.5)

wins2 = find_qq_windows()
print(f'窗口数: {len(wins2)}')
for w in wins2:
    print(f'  {w}')
