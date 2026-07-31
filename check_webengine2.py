# -*- coding: utf-8 -*-
"""对比 _python 源环境与产物中 WebEngine DLL"""
import os

SRC_BIN = r"D:\7tan\7tanAI\dist\_python\Lib\site-packages\PyQt6\Qt6\bin"
DST_BIN = r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PyQt6\Qt6\bin"

keys = ["libEGL", "libGLESv2", "d3dcompiler", "icu", "QtWebEngineProcess", "Qt6WebEngineCore"]

print("=== 源环境 PyQt6\\Qt6\\bin 关键文件 ===")
if os.path.isdir(SRC_BIN):
    for f in sorted(os.listdir(SRC_BIN)):
        if any(k.lower() in f.lower() for k in keys):
            size = os.path.getsize(os.path.join(SRC_BIN, f)) / 1024 / 1024
            print("  ", f, f"{size:.1f}MB")
else:
    print("  ❌ 源环境 bin 不存在:", SRC_BIN)

print("\n=== 产物中对应文件 ===")
for f in ["libEGL.dll", "libGLESv2.dll", "d3dcompiler_47.dll"]:
    p = os.path.join(DST_BIN, f)
    print("  ", f, "✅ 存在" if os.path.exists(p) else "❌ 缺失")

print("\n=== 源环境 bin 总文件数 vs 产物 ===")
print("  源:", len(os.listdir(SRC_BIN)) if os.path.isdir(SRC_BIN) else "N/A")
print("  产物:", len(os.listdir(DST_BIN)) if os.path.isdir(DST_BIN) else "N/A")
