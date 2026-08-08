# -*- coding: utf-8 -*-
"""检查 QQ 进程和窗口状态"""
import psutil
import ctypes
import ctypes.wintypes as wt
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. 进程
print('=== QQ 相关进程 ===')
found = False
for p in psutil.process_iter(['pid', 'name', 'exe']):
    try:
        name = (p.info['name'] or '').lower()
        exe = (p.info['exe'] or '').lower()
        if 'qq' in name or 'qq' in exe:
            found = True
            print(f"  PID={p.info['pid']} name={p.info['name']} exe={exe}")
    except Exception:
        pass
if not found:
    print('  未找到 QQ 进程！')

# 2. 窗口
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

def get_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

qq_windows = []

@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_cb(hwnd, lparam):
    if not user32.IsWindowVisible(hwnd):
        return True
    pid = get_pid(hwnd)
    try:
        proc = psutil.Process(pid)
        exe = (proc.exe() or '').lower()
        if 'qq' in exe:
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            qq_windows.append((hwnd, buf.value, pid, rect.left, rect.top, rect.right, rect.bottom))
    except Exception:
        pass
    return True

user32.EnumWindows(enum_cb, 0)
print(f'\n=== QQ 可见窗口: {len(qq_windows)} 个 ===')
for hwnd, title, pid, l, t, r, b in qq_windows:
    print(f'  HWND={hwnd} 标题={title!r} rect=({l},{t},{r},{b}) 尺寸=({r-l}x{b-t})')
