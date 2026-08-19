# -*- coding: utf-8 -*-
"""重新枚举QQ窗口状态：位置、可见性、最小化状态"""
import ctypes
import ctypes.wintypes as wt
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_MINIMIZE = 6

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
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if h:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            path = buf.value.lower()
            if 'qq' in path and path.endswith('.exe'):
                length = user32.GetWindowTextLengthW(hwnd)
                tbuf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, tbuf, length + 1)
                qq_windows.append((hwnd, tbuf.value, pid))
        kernel32.CloseHandle(h)
    return True

user32.EnumWindows(enum_cb, 0)

for hwnd, title, pid in qq_windows:
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    minimized = user32.IsIconic(hwnd)
    maximized = user32.IsZoomed(hwnd)
    focused = (user32.GetForegroundWindow() == hwnd)
    print(f"HWND={hwnd} 标题='{title}' rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) "
          f"最小化={minimized} 最大化={maximized} 前台={focused}")
