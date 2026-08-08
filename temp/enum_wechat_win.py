# -*- coding: utf-8 -*-
"""枚举所有窗口（含最小化/隐藏），定位微信窗口"""
import ctypes, sys
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 找 Weixin.exe 进程的 PID
import subprocess
out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Weixin.exe', '/FO', 'CSV'],
                     capture_output=True, text=True).stdout
pids = set()
for line in out.splitlines()[1:]:
    parts = line.strip('"').split('","')
    if len(parts) > 1 and parts[1].strip().isdigit():
        pids.add(int(parts[1].strip()))
print('Weixin PIDs:', pids)

results = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def enum_callback(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in pids:
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if title.strip():
            visible = user32.IsWindowVisible(hwnd)
            minimized = user32.IsIconic(hwnd)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            results.append((hwnd, title, visible, minimized,
                            (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)))
    return True

user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
for hwnd, title, visible, minimized, rect in results:
    print(f'hwnd={hwnd} title="{title}" visible={visible} minimized={minimized} rect={rect}')
if not results:
    print('⚠️ 未找到微信窗口（可能完全隐藏或驻留托盘）')
print('DONE')
