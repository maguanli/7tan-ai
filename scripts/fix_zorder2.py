# -*- coding: utf-8 -*-
"""检查并修复 z-order：确保 QQ 395876 在 7Tan 之上"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32

def get_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def get_rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)

print('=== 置顶前 z-order（前6） ===')
hwnd = user32.GetTopWindow(None)
cnt = 0
while hwnd and cnt < 6:
    if user32.IsWindowVisible(hwnd):
        print(f"  {hwnd} '{get_title(hwnd)[:30]}' {get_rect(hwnd)}")
        cnt += 1
    hwnd = user32.GetWindow(hwnd, 2)

# 置顶 QQ
QQ_HWND = 395876
user32.ShowWindow(QQ_HWND, 9)
time.sleep(0.2)
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)
print(f'\n前台: {user32.GetForegroundWindow()} (期望 {QQ_HWND})')

print('\n=== 置顶后 z-order（前6） ===')
hwnd = user32.GetTopWindow(None)
cnt = 0
while hwnd and cnt < 6:
    if user32.IsWindowVisible(hwnd):
        print(f"  {hwnd} '{get_title(hwnd)[:30]}' {get_rect(hwnd)}")
        cnt += 1
    hwnd = user32.GetWindow(hwnd, 2)
