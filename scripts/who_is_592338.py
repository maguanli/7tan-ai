# -*- coding: utf-8 -*-
"""查询前台窗口 592338 的身份"""
import ctypes
import ctypes.wintypes as wt
import sys
import psutil

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
hwnd = 592338

length = user32.GetWindowTextLengthW(hwnd)
buf = ctypes.create_unicode_buffer(length + 1)
user32.GetWindowTextW(hwnd, buf, length + 1)
print(f'标题: {buf.value!r}')

cls = ctypes.create_unicode_buffer(256)
user32.GetClassNameW(hwnd, cls, 256)
print(f'类名: {cls.value}')

pid = wt.DWORD()
user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
print(f'PID: {pid.value}')
try:
    p = psutil.Process(pid.value)
    print(f'进程: {p.name()} exe={p.exe()}')
except Exception as e:
    print(f'进程查询失败: {e}')

rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f'位置: ({rect.left},{rect.top},{rect.right},{rect.bottom})')

# 顺便看当前所有前台候选窗口
print('\n=== 所有 python/QQ 可见窗口 ===')
for p in psutil.process_iter(['pid', 'name']):
    try:
        if p.info['name'] and p.info['name'].lower() in ('python.exe', 'qq.exe'):
            pass
    except Exception:
        pass

@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_cb(h, lp):
    if not user32.IsWindowVisible(h):
        return True
    p = wt.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(p))
    try:
        proc = psutil.Process(p.value)
        n = proc.name()
    except Exception:
        return True
    if n.lower() in ('python.exe', 'qq.exe'):
        ln = user32.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(ln + 1)
        user32.GetWindowTextW(h, b, ln + 1)
        r = wt.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        if r.right - r.left > 50 and r.bottom - r.top > 50:
            print(f'  hwnd={h} "{b.value[:40]}" ({r.left},{r.top},{r.right-r.left}x{r.bottom-r.top})')
    return True

user32.EnumWindows(enum_cb, 0)
