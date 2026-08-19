import subprocess
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW

# 用 wmic 获取 Weixin.exe 的 PID（更可靠）
out = subprocess.run(["wmic", "process", "where", "name='Weixin.exe'", "get", "ProcessId"],
                     capture_output=True, text=True).stdout
weixin_pids = set()
for line in out.splitlines():
    line = line.strip()
    if line.isdigit():
        weixin_pids.add(int(line))

print("Weixin PIDs:", weixin_pids)

windows = []

def callback(hwnd, lparam):
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in weixin_pids:
        length = GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        visible = IsWindowVisible(hwnd)
        windows.append((hwnd, pid.value, buf.value, visible))
    return True

EnumWindows(EnumWindowsProc(callback), 0)

for w in windows:
    print(f"hwnd={w[0]} pid={w[1]} title='{w[2]}' visible={w[3]}")
if not windows:
    print("NO WINDOWS FOUND for Weixin.exe")
