# -*- coding: utf-8 -*-
"""检查前台窗口 + 枚举QQ窗口子控件"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import win32gui, win32con, ctypes

QQ_HWND = 131828

fg = win32gui.GetForegroundWindow()
print('foreground:', fg, repr(win32gui.GetWindowText(fg)))

# 尝试再次激活QQ
win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
win32gui.SetWindowPos(QQ_HWND, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
win32gui.SetWindowPos(QQ_HWND, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
win32gui.SetForegroundWindow(QQ_HWND)
time.sleep(1)
fg2 = win32gui.GetForegroundWindow()
print('foreground after activate:', fg2, repr(win32gui.GetWindowText(fg2)))

# 枚举QQ窗口的子窗口
def enum_child(hwnd, lparam):
    t = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    try:
        rect = win32gui.GetWindowRect(hwnd)
    except Exception:
        rect = None
    print(f'  child {hwnd} class={cls!r} text={t!r} rect={rect}')
    return True

print('--- children of QQ ---')
win32gui.EnumChildWindows(QQ_HWND, enum_child, None)
print('DONE')
