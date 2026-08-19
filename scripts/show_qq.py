# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 找 QQ 主窗口
results = []
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def callback(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    # 检查窗口标题
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        # 检查进程名
        if pid.value in (6272, 6468, 1708, 12996, 8188, 13572, 11708, 448):
            visible = user32.IsWindowVisible(hwnd)
            results.append((hwnd, pid.value, title, visible))
    return True

user32.EnumWindows(EnumWindowsProc(callback), 0)

print('=== QQ 进程窗口 ===')
for hwnd, pid, title, visible in results:
    print(f'hwnd={hwnd} pid={pid} visible={visible} title={repr(title)}')

# 尝试显示第一个可见或主窗口
if results:
    # 优先找可见的主窗口
    target = None
    for hwnd, pid, title, visible in results:
        if visible and title:
            target = hwnd
            break
    if target is None and results:
        target = results[0][0]
    if target:
        print(f'\n调用 ShowWindow 显示 hwnd={target}')
        user32.ShowWindow(target, 9)  # SW_RESTORE
        user32.SetForegroundWindow(target)
        print('已尝试恢复窗口')
