# -*- coding: utf-8 -*-
"""检查 WebEngine 配套文件 + PyQt6 pyd + 直接复现 exe 错误"""
import os, subprocess, sys

ROOT = r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PyQt6\Qt6"

print("=== Qt6\\bin 关键 DLL（EGL/GLES/icu/d3d/WebEngineProcess）===")
keys = ["libEGL", "libGLESv2", "icu", "d3dcompiler", "QtWebEngineProcess", "qwebengine"]
if os.path.isdir(ROOT):
    for f in sorted(os.listdir(os.path.join(ROOT, "bin"))):
        low = f.lower()
        if any(k.lower() in low for k in keys):
            full = os.path.join(ROOT, "bin", f)
            print(" ", f, f"{os.path.getsize(full)/1024/1024:.1f}MB")

print("\n=== resources 目录 ===")
res = os.path.join(ROOT, "resources")
if os.path.isdir(res):
    for f in sorted(os.listdir(res)):
        print(" ", f)
else:
    print("  ❌ resources 目录不存在！")

print("\n=== translations 目录 ===")
tr = os.path.join(ROOT, "translations")
if os.path.isdir(tr):
    print("  ", len(os.listdir(tr)), "个文件")
else:
    print("  ❌ translations 目录不存在！")

print("\n=== PyQt6 顶层 .pyd ===")
pq = r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PyQt6"
if os.path.isdir(pq):
    for f in sorted(os.listdir(pq)):
        if f.endswith(".pyd"):
            print(" ", f)
