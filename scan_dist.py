# -*- coding: utf-8 -*-
"""递归扫描 7tan-editor 产物中的 DLL 与 Qt 相关文件"""
import os

ROOT = r"D:\7tan\7tanAI\dist\7tan-editor"

print("=== 全部 DLL（递归）===")
dll_count = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        if f.lower().endswith(".dll"):
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
            dll_count += 1
            print(" ", rel)

print(f"\nDLL 总数: {dll_count}")

print("\n=== 顶层目录结构 ===")
for name in sorted(os.listdir(ROOT)):
    full = os.path.join(ROOT, name)
    print(" ", name, "<DIR>" if os.path.isdir(full) else f"{os.path.getsize(full)/1024/1024:.1f}MB")

print("\n=== PyQt6 相关目录 ===")
for dirpath, dirnames, filenames in os.walk(ROOT):
    for d in dirnames:
        if "qt" in d.lower():
            print(" ", os.path.relpath(os.path.join(dirpath, d), ROOT))
