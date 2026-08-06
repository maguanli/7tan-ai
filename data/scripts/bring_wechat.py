import sys
import ctypes
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

u = ctypes.windll.user32

# 1. 最小化管理员 PowerShell 窗口 (1901928)
r1 = u.ShowWindow(1901928, 6)  # SW_MINIMIZE
print("minimize powershell:", r1, flush=True)

# 2. 恢复并置顶微信 (329388)
r2 = u.ShowWindow(329388, 9)   # SW_RESTORE
print("restore wechat:", r2, flush=True)
u.SetForegroundWindow(329388)
time.sleep(0.8)

# 3. 查看两个 python 进程的主窗口标题，确认身份
import subprocess
ps = (
    "powershell -NoProfile -Command "
    "\"Get-Process -Id 10912,9416 -ErrorAction SilentlyContinue | "
    "Select-Object Id, ProcessName, MainWindowTitle | Format-List | Out-String -Width 300\""
)
r = subprocess.run(ps, capture_output=True, text=True, timeout=20)
print(r.stdout[:2000], flush=True)
if r.stderr:
    print("ERR:", r.stderr[:500], flush=True)
