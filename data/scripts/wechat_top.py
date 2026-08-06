import sys
import ctypes
import ctypes.wintypes as wt
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

u = ctypes.windll.user32
hwnd = 329388

r = wt.RECT()
u.GetWindowRect(hwnd, ctypes.byref(r))
print("wechat rect:", (r.left, r.top, r.right, r.bottom), flush=True)
print("visible:", u.IsWindowVisible(hwnd), flush=True)
print("fg before:", u.GetForegroundWindow(), flush=True)

# 强制置顶微信
u.ShowWindow(hwnd, 9)  # SW_RESTORE
u.SetForegroundWindow(hwnd)
time.sleep(0.6)
print("fg after:", u.GetForegroundWindow(), flush=True)
