# -*- coding: utf-8 -*-
"""真实鼠标双击桌面 QQ 图标（模拟人工点击），然后验证 QQ 窗口状态"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import ctypes
import ctypes.wintypes as wt
import pyautogui

user32 = ctypes.windll.user32
FindWindowW = user32.FindWindowW
FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
FindWindowW.restype = wt.HWND
GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int
IsWindowVisible = user32.IsWindowVisible
IsWindowVisible.argtypes = [wt.HWND]
IsWindowVisible.restype = ctypes.c_bool

# 1. 双击桌面 QQ 图标（图标中心约 50,615，稍偏图标图形区域 60,610）
QQ_ICON_POS = (60, 610)
print(f"1. 移动鼠标到 QQ 图标 {QQ_ICON_POS} 并双击...")
pyautogui.moveTo(QQ_ICON_POS[0], QQ_ICON_POS[1], duration=0.3)
time.sleep(0.5)
pyautogui.doubleClick(QQ_ICON_POS[0], QQ_ICON_POS[1], interval=0.15)
print("   已双击")
time.sleep(4)

# 2. 枚举所有窗口，找 QQ 相关窗口
print("\n2. 当前 QQ 相关窗口：")
def enum_proc(hwnd, lparam):
    if not IsWindowVisible(hwnd):
        return True
    length = GetWindowTextW(hwnd, None, 0)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if "QQ" in title or "7723" in title or "腾讯" in title:
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            print(f"   hwnd={hwnd} title={title!r} rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

# 3. 检查 QQ 进程
print("\n3. QQ 进程：")
import subprocess
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq QQ.exe", "/FO", "CSV"], capture_output=True, text=True, encoding="gbk", errors="replace")
print(r.stdout.strip() or "无 QQ.exe 进程")
r2 = subprocess.run(["tasklist", "/FI", "IMAGENAME eq QQ.exe", "/FO", "CSV"], capture_output=True, text=True, encoding="gbk", errors="replace")
