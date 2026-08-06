# -*- coding: utf-8 -*-
"""按进程名查找微信窗口（含不可见窗口）"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

def get_pid_by_name(name):
    """通过 CreateToolhelp32Snapshot 找进程 PID"""
    TH32CS_SNAPPROCESS = 0x00000002
    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == -1:
        return []
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    pids = []
    if kernel32.Process32First(snapshot, ctypes.byref(entry)):
        while True:
            if entry.szExeFile.decode('ascii', errors='ignore').lower() == name.lower():
                pids.append(entry.th32ProcessID)
            if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                break
    kernel32.CloseHandle(snapshot)
    return pids

def get_pid_for_hwnd(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

pids = get_pid_by_name('Weixin.exe')
print('Weixin.exe PIDs:', pids)
if not pids:
    pids = get_pid_by_name('WeChat.exe')
    print('WeChat.exe PIDs:', pids)

pid_set = set(pids)
windows = []

@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lparam):
    pid = get_pid_for_hwnd(hwnd)
    if pid in pid_set:
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        visible = user32.IsWindowVisible(hwnd)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        windows.append((hwnd, buf.value, cls.value, visible,
                        rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
    return True

user32.EnumWindows(cb, 0)
print('Weixin windows found:', len(windows))
for hwnd, title, cls, vis, l, t, w, h in windows:
    print(f'  hwnd={hwnd} title={title!r} class={cls!r} visible={vis} rect=({l},{t},{w}x{h})')
print('DONE')
