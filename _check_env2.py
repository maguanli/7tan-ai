# -*- coding: utf-8 -*-
"""检查备份产物结构 + _python 环境关键包"""
import os, subprocess, sys

# 1. 备份产物 _internal 关键文件
d = r"D:\7tan\7tanAI\dist\7tan-editor_bak_20260801\_internal"
files = os.listdir(d)
print("=== 备份产物 _internal (%d 项) ===" % len(files))
for f in sorted(files):
    if f.endswith((".pyz", ".dll", ".zip")) or "python312" in f:
        print("  ", f, os.path.getsize(os.path.join(d, f)))

# 2. security pyd
sec = os.path.join(d, "src", "security")
if os.path.exists(sec):
    print("\n=== 备份产物 src/security ===")
    for f in sorted(os.listdir(sec)):
        print("  ", f)
else:
    print("\n=== 备份产物 src/security 不存在! ===")

# 3. _python 关键包
print("\n=== _python 关键包 ===")
pkgs = ["cryptography", "PyQt6", "playwright", "pyinstaller", "openai",
        "fastapi", "uvicorn", "oss2", "sqlalchemy", "pydantic", "httpx",
        "yaml", "apscheduler", "loguru", "PIL", "numpy", "Cython"]
r = subprocess.run([r"D:\7tan\7tanAI\dist\_python\python.exe", "-m", "pip", "list"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
installed = r.stdout.lower()
missing = [p for p in pkgs if p.lower() not in installed]
print("缺失包:", missing if missing else "全部齐全")
# 打印版本
for line in r.stdout.splitlines():
    for p in pkgs:
        if line.lower().startswith(p.lower()):
            print("  ", line)
            break
