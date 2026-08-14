import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

hwnd = 263840  # 微信主窗口

# ShowWindow: SW_RESTORE = 9
result = user32.ShowWindow(hwnd, 9)
print("ShowWindow(SW_RESTORE) result:", result)

# SetForegroundWindow 激活
result2 = user32.SetForegroundWindow(hwnd)
print("SetForegroundWindow result:", result2)

# 再检查可见性
IsWindowVisible = user32.IsWindowVisible
print("IsWindowVisible:", IsWindowVisible(hwnd))
