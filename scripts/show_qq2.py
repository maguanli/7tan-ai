# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

results = []
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def callback(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if pid.value in (6272, 6468, 1708, 12996, 8188, 13572, 11708, 448) and title == 'QQ':
            # 只处理顶层可见性窗口
            visible = user32.IsWindowVisible(hwnd)
            results.append((hwnd, pid.value, title, visible))
    return True

user32.EnumWindows(EnumWindowsProc(callback), 0)

print('QQ 主窗口候选:', results)

shown = []
for hwnd, pid, title, visible in results:
    # 尝试显示
    user32.ShowWindow(hwnd, 5)  # SW_SHOW
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)  # HWND_TOPMOST + NOMOVE + NOSIZE + SHOWWINDOW
    shown.append(hwnd)

time.sleep(2)
# 再确认可见性
for hwnd, pid, title, visible in results:
    vis = user32.IsWindowVisible(hwnd)
    print(f'hwnd={hwnd} now_visible={vis}')

# 置前最后一个（通常主窗口）
if shown:
    user32.SetForegroundWindow(shown[0])
    print('已置前:', shown[0])
