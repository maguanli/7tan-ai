# -*- coding: utf-8 -*-
"""查找微信真实进程名 + 权限检测（修正版）"""
import ctypes, sys, subprocess, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from ctypes import wintypes

# 1. 列出所有含 wei/chat/weixin 的进程
r = subprocess.run(["tasklist"], capture_output=True, text=True, encoding="gbk", errors="replace")
print("=== 疑似微信进程 ===")
for line in r.stdout.splitlines():
    if re.search(r"weixin|wechat|wechatapp|微信", line, re.I):
        print(" ", line.strip())

# 2. 权限检测函数（用 GetTokenInformation TokenElevation）
def get_elevation(pid):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    TOKEN_QUERY = 0x0008
    TokenElevation = 20
    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32
    hProc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProc:
        return f"OpenProcess失败 err={kernel32.GetLastError()}"
    hTok = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(hProc, TOKEN_QUERY, ctypes.byref(hTok)):
        return f"OpenProcessToken失败 err={kernel32.GetLastError()}"
    elev = wintypes.DWORD()
    size = wintypes.DWORD()
    ok = advapi32.GetTokenInformation(hTok, TokenElevation, ctypes.byref(elev), ctypes.sizeof(elev), ctypes.byref(size))
    kernel32.CloseHandle(hTok)
    kernel32.CloseHandle(hProc)
    if not ok:
        return f"GetTokenInformation失败 err={kernel32.GetLastError()}"
    return bool(elev.value)

# 当前进程
print(f"\n当前进程(脚本)管理员: {get_elevation(ctypes.windll.kernel32.GetCurrentProcessId())}")

# 对每个疑似微信 PID 检测
for line in r.stdout.splitlines():
    if re.search(r"weixin|wechat", line, re.I):
        m = re.search(r"(\d+)\s", line)
        if m:
            pid = int(m.group(1))
            print(f"进程 {line.split()[0]} PID={pid} 管理员: {get_elevation(pid)}")
