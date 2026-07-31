# -*- coding: utf-8 -*-
"""检查 _python 便携环境的 PyQt6 等关键依赖"""
import os, subprocess, sys

SP = r"D:\7tan\7tanAI\dist\_python\Lib\site-packages"

print("=== site-packages 中含 Qt/PyQt 的目录 ===")
for name in sorted(os.listdir(SP)):
    if "qt" in name.lower() or "pyqt" in name.lower():
        print(" ", name)

print("\n=== pip list 关键包 ===")
out = subprocess.run(
    [r"D:\7tan\7tanAI\dist\_python\python.exe", "-m", "pip", "list"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
).stdout
for line in out.splitlines():
    low = line.lower()
    if any(k in low for k in ["pyqt", "qt6", "pyinstaller", "cryptography", "playwright", "numpy"]):
        print(" ", line)
