import sys
import ctypes
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

u = ctypes.windll.user32

# 最小化监控窗口 984354，避免遮挡微信
r = u.ShowWindow(984354, 6)
print("minimize monitor:", r, flush=True)

# 微信置顶
u.SetForegroundWindow(329388)
time.sleep(0.8)
print("done", flush=True)
