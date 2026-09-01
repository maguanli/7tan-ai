# -*- coding: utf-8 -*-
"""快速搜索本机可用的浏览器可执行文件（用于HTML渲染截图）"""
import os

targets = ["chrome.exe", "msedge.exe", "chromium.exe", "msedge_beta.exe"]
found = []

# 候选根目录（浅层扫描，控制耗时）
roots = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
    os.path.expandvars(r"%LOCALAPPDATA%\Google"),
    os.path.expandvars(r"%LOCALAPPDATA%\Chromium"),
    r"D:\\",
]

skip_names = {"Windows", "System Volume Information", "$Recycle.Bin", "node_modules",
              ".git", "__pycache__", "WindowsApps", "Temp", "Downloads"}

for root in roots:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth > 4:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in skip_names]
        for f in filenames:
            if f.lower() in targets:
                p = os.path.join(dirpath, f)
                try:
                    size_mb = os.path.getsize(p) / 1048576
                    if size_mb > 30:  # 真正的浏览器主程序都很大
                        found.append((p, round(size_mb, 1)))
                except OSError:
                    pass

if found:
    print("FOUND:")
    for p, mb in found:
        print(f"  {p}  ({mb} MB)")
else:
    print("NO_BROWSER_FOUND")
