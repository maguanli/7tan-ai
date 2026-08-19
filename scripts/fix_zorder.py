# -*- coding: utf-8 -*-
"""枚举顶层窗口 z-order，确认 7Tan 与 QQ 的遮挡关系，并置顶 QQ"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

def get_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def get_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def get_exe(pid):
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ''
    buf = ctypes.create_unicode_buffer(1024)
    size = wt.DWORD(1024)
    ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
    kernel32.CloseHandle(h)
    return buf.value if ok else ''

def get_rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)

# 1. 枚举 z-order（从桌面向下）
print('=== 顶层窗口 z-order（从上到下） ===')
hwnd = user32.GetTopWindow(None)
order = []
while hwnd:
    if user32.IsWindowVisible(hwnd):
        title = get_title(hwnd)
        exe = get_exe(get_pid(hwnd))
        rect = get_rect(hwnd)
        order.append((hwnd, title, exe, rect))
        print(f"  {hwnd} '{title}' {exe.split(chr(92))[-1]} {rect}")
    hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT

# 2. 置顶 QQ 1443834
print('\n=== 置顶 QQ 1443834 ===')
QQ_HWND = 1443834
user32.ShowWindow(QQ_HWND, 9)
time.sleep(0.2)
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # TOPMOST
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)
print(f'前台: {user32.GetForegroundWindow()} (期望 1443834)')

# 3. 再枚举 z-order 确认
print('\n=== 置顶后 z-order 前 8 个 ===')
hwnd = user32.GetTopWindow(None)
cnt = 0
while hwnd and cnt < 8:
    if user32.IsWindowVisible(hwnd):
        print(f"  {hwnd} '{get_title(hwnd)}' {get_exe(get_pid(hwnd)).split(chr(92))[-1]} {get_rect(hwnd)}")
        cnt += 1
    hwnd = user32.GetWindow(hwnd, 2)

# 4. 截图验证 QQ 区域显示内容
import pyautogui
img = pyautogui.screenshot(region=(480, 200, 1060, 640))
img.save(r'D:\7tan\7tanAI\scripts\qq_verify_top.png')
print('\n已截图 qq_verify_top.png，用于 OCR 验证')
