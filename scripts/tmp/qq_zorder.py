import sys, ctypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import win32gui, win32con

user32 = ctypes.windll.user32
# 枚举窗口按 z-order 从上到下
order = []
hwnd = user32.GetTopWindow(None)
while hwnd:
    if win32gui.IsWindowVisible(hwnd):
        t = win32gui.GetWindowText(hwnd)
        if t.strip():
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                rect = None
            order.append((hwnd, t.strip(), rect))
    hwnd = user32.GetWindow(hwnd, win32con.GW_HWNDNEXT)

for i, (h, t, r) in enumerate(order):
    print(f'#{i} {h} | {r} | {t!r}')
