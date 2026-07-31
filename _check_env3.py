# -*- coding: utf-8 -*-
import os, subprocess

DIST = r"D:\7tan\7tanAI\dist"
APP = os.path.join(DIST, "7tan-editor")

print("=== 7tan-editor 目录 ===")
if os.path.exists(APP):
    for f in sorted(os.listdir(APP)):
        full = os.path.join(APP, f)
        print("  ", f, "DIR" if os.path.isdir(full) else "%dB" % os.path.getsize(full))
else:
    print("  不存在!")

internal = os.path.join(APP, "_internal")
print("\n=== _internal 关键文件 ===")
if os.path.exists(internal):
    files = os.listdir(internal)
    print("  总数:", len(files))
    for f in sorted(files):
        if f.endswith((".pyz", ".dll")) or "python312" in f or "base_library" in f:
            full = os.path.join(internal, f)
            print("   ", f, "%dB" % os.path.getsize(full))
else:
    print("  不存在!")

sec = os.path.join(internal, "src", "security")
print("\n=== _internal/src/security ===")
if os.path.exists(sec):
    for f in sorted(os.listdir(sec)):
        print("   ", f)
else:
    print("  不存在!")

# 全部 pyd 统计
print("\n=== _internal 下所有 .pyd ===")
for root, dirs, files in os.walk(internal):
    for f in files:
        if f.endswith(".pyd"):
            print("   ", os.path.relpath(os.path.join(root, f), internal))

# _python 包
print("\n=== _python 关键包 ===")
pkgs = ["cryptography", "PyQt6", "playwright", "pyinstaller", "openai",
        "fastapi", "uvicorn", "oss2", "sqlalchemy", "pydantic", "httpx",
        "yaml", "apscheduler", "loguru", "PIL", "numpy", "Cython", "jedi", "feedparser"]
r = subprocess.run([r"D:\7tan\7tanAI\dist\_python\python.exe", "-m", "pip", "list"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
installed = r.stdout.lower()
missing = [p for p in pkgs if p.lower() not in installed]
print("缺失:", missing if missing else "全部齐全")
for line in r.stdout.splitlines():
    low = line.lower()
    for p in pkgs:
        if low.startswith(p.lower() + " ") or low.startswith(p.lower() + "-"):
            print("  ", line.strip())
            break
