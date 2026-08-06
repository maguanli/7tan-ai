# -*- coding: utf-8 -*-
"""检测微信进程与当前进程的管理员权限（UIPI 隔离检查）"""
import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from ctypes import wintypes

# 找到微信进程 PID
import subprocess
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq wechat.exe", "/FO", "CSV"],
                   capture_output=True, text=True, encoding="gbk", errors="replace")
print("=== wechat.exe 进程 ===")
print(r.stdout)

# 检查提权状态
def is_elevated(pid=None):
    TOKEN_QUERY = 0x0008
    TokenElevation = 20
    hProc = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid) if pid else ctypes.windll.kernel32.GetCurrentProcess()
    if not hProc:
        return None
    hTok = wintypes.HANDLE()
    if not ctypes.windll.advapi32.OpenProcessToken(hProc, TOKEN_QUERY, ctypes.byref(hTok)):
        return None
    elev = wintypes.DWORD()
    size = wintypes.DWORD()
    ok = ctypes.windll.advapi32.GetTokenInformation(hTok, TokenElevation, ctypes.byref(elev), 4, ctypes.byref(size))
    if hTok:
        ctypes.windll.kernel32.CloseHandle(hTok)
    if hProc and pid:
        ctypes.windll.kernel32.CloseHandle(hProc)
    return bool(elev.value) if ok else None

print("\n=== 权限检测 ===")
print(f"当前脚本进程是否管理员: {is_elevated()}")

# 找微信 PID
import re
for line in r.stdout.splitlines():
    if "wechat" in line.lower():
        m = re.findall(r'"(\d+)"', line)
        if m:
            pid = int(m[0])
            elev = is_elevated(pid)
            print(f"微信 PID={pid} 是否管理员: {elev}")
            break
