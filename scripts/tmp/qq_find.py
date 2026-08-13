# -*- coding: utf-8 -*-
import os, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== 常见安装路径 ===")
paths = [
    r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
    r"C:\Program Files\Tencent\QQ\Bin\QQ.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tencent\QQ\Bin\QQ.exe"),
    r"D:\Program Files\Tencent\QQ\Bin\QQ.exe",
    r"D:\Tencent\QQ\Bin\QQ.exe",
    r"D:\Software\Tencent\QQ\Bin\QQ.exe",
]
for p in paths:
    print(p, "->", os.path.exists(p))

print("=== 全盘搜索 QQ.exe（常见盘符）===")
for drive in ["C:\\", "D:\\", "E:\\"]:
    if not os.path.exists(drive):
        continue
    for root, dirs, files in os.walk(drive):
        # 跳过太深的目录
        depth = root.count("\\")
        if depth > 5:
            dirs[:] = []
            continue
        try:
            if "QQ.exe" in files and ("Tencent" in root or "QQ" in root):
                print("FOUND:", os.path.join(root, "QQ.exe"))
                dirs[:] = []
        except PermissionError:
            pass

print("=== 桌面快捷方式 ===")
for d in [os.path.join(os.path.expanduser("~"), "Desktop"), r"C:\Users\Public\Desktop"]:
    if os.path.isdir(d):
        for f in os.listdir(d):
            if "qq" in f.lower() or "tencent" in f.lower():
                print(os.path.join(d, f))

print("=== 开始菜单快捷方式 ===")
start = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
for root, dirs, files in os.walk(start):
    for f in files:
        if "qq" in f.lower() or "腾讯" in f:
            print(os.path.join(root, f))
