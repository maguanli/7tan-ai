# -*- coding: utf-8 -*-
"""检查微信进程状态"""
import sys, subprocess, re, ctypes, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

r = subprocess.run(["tasklist"], capture_output=True, text=True, encoding="gbk", errors="replace")
weixin = [l for l in r.stdout.splitlines() if "Weixin" in l or "wechat" in l.lower()]
print(f"=== Weixin.exe 进程数: {len(weixin)} ===")
for l in weixin[:5]:
    print(" ", l.strip())

# 找微信安装路径（注册表）
import winreg
paths = []
try:
    for key in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Weixin.exe",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\Weixin.exe"]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
                p = winreg.QueryValue(k, None)
                paths.append(p)
        except Exception:
            pass
except Exception as e:
    print("注册表读取失败:", e)

if paths:
    print(f"微信安装路径(注册表): {paths}")
else:
    # 常见路径
    import os
    candidates = [
        r"C:\Program Files\Tencent\Weixin\Weixin.exe",
        r"C:\Program Files (x86)\Tencent\Weixin\Weixin.exe",
        r"D:\Program Files\Tencent\Weixin\Weixin.exe",
        r"C:\Program Files\Tencent\WeChat\WeChat.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Tencent\Weixin\Weixin.exe"),
        os.path.expandvars(r"%APPDATA%\Tencent\Weixin\Weixin.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            print(f"微信路径(常见位置): {p}")
            paths.append(p)
    if not paths:
        print("未找到微信安装路径")
