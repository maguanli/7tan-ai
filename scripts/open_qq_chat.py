# -*- coding: utf-8 -*-
"""双击QQ消息区域打开独立聊天窗口，然后检查新窗口"""
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
        wins.append((h, r.left, r.top, w, hh, cls.value))
        return True
    user32.EnumWindows(enum_cb, 0)
    return wins

print('=== 操作前 QQ 窗口 ===')
wins = find_qq_windows()
for w in wins:
    print(f'  {w}')

# 找大窗口并置顶
big = [w for w in wins if w[3] > 300 and w[4] > 300]
if not big:
    print('没有大窗口')
    sys.exit(1)
QQ_HWND = max(big, key=lambda x: x[3]*x[4])[0]
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)
print(f'前台: {user32.GetForegroundWindow()}')

# 双击消息区域（群消息显示在窗口中间偏左）
print('双击 (700, 500) 打开聊天窗口...')
pyautogui.doubleClick(700, 500)
time.sleep(1.5)

print('\n=== 操作后 QQ 窗口 ===')
wins2 = find_qq_windows()
for w in wins2:
    print(f'  {w}')

new_wins = [w for w in wins2 if w[3] > 300 and w[4] > 300]
print(f'\n大窗口数量: {len(new_wins)} (之前 {len(big)})')
