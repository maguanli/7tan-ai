# -*- coding: utf-8 -*-
"""检查 PyInstaller 进程是否存活 + build_log 是否增长"""
import subprocess, os, time

# 1. 看 _python 的进程
out = subprocess.run(["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine", "/format:list"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
print("=== python.exe 进程 ===")
for block in out.split("\n\n"):
    if "PyInstaller" in block or "pyinstaller" in block or "_python" in block:
        print(block[:500])

# 2. build_log.txt 大小（等 5 秒看是否增长）
p = r"D:\7tan\7tanAI\dist\build_log.txt"
s1 = os.path.getsize(p) if os.path.exists(p) else 0
time.sleep(5)
s2 = os.path.getsize(p) if os.path.exists(p) else 0
print(f"\nbuild_log.txt: {s1} 字节 -> 5秒后 {s2} 字节 {'（仍在增长）' if s2 > s1 else '（已停止）'}")
