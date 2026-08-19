# -*- coding: utf-8 -*-
"""枚举所有可见窗口及进程信息，检查 QQ/微信窗口状态"""
import ctypes
import ctypes.wintypes as wt
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
OpenProcess = kernel32.OpenProcess
QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
GetLastError = kernel32.GetLastError

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

def get_process_path(pid):
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    buf = ctypes.create_unicode_buffer(1024)
    size = wt.DWORD(1024)
    ok = QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
    kernel32.CloseHandle(h)
    return buf.value if ok else None

windows = []

@EnumWindowsProc
def cb(hwnd, lparam):
    if not IsWindowVisible(hwnd):
        return True
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return True
    buf = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    if not title.strip():
        return True
    pid = wt.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    windows.append((hwnd, title, pid.value))
    return True

EnumWindows(cb, 0)

print(f"共发现 {len(windows)} 个可见窗口:\n")
for hwnd, title, pid in windows:
    path = get_process_path(pid) or ""
    print(f"[{pid}] {title}")
    print(f"      exe: {path}")
