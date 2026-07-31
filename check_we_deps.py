# -*- coding: utf-8 -*-
"""检查 Qt6WebEngineCore.dll 依赖 vs 产物实际 DLL"""
import os, subprocess

OBJDUMP = r"D:\7tan\mingw64\bin\objdump.exe"
SRC = r"D:\7tan\7tanAI\dist\_python\Lib\site-packages\PyQt6\Qt6\bin\Qt6WebEngineCore.dll"
DST_INTERNAL = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"

# 1. 源 Qt6WebEngineCore.dll 的依赖
out = subprocess.run([OBJDUMP, "-p", SRC], capture_output=True, text=True,
                     encoding="utf-8", errors="replace").stdout
deps = [l.split("DLL Name:")[1].strip() for l in out.splitlines() if "DLL Name:" in l]
print("=== Qt6WebEngineCore.dll 依赖 (%d 个) ===" % len(deps))
for d in deps:
    print("  ", d)

# 2. 产物中所有 DLL 文件名（递归）
have = set()
for dirpath, dirnames, filenames in os.walk(DST_INTERNAL):
    for f in filenames:
        if f.lower().endswith(".dll") or f.lower().endswith(".exe"):
            have.add(f.lower())
print("\n=== 产物缺失的依赖 DLL ===")
missing = [d for d in deps if d.lower() not in have and d.lower() not in ("kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll", "ole32.dll", "oleaut32.dll", "ws2_32.dll", "winmm.dll", "shlwapi.dll", "comdlg32.dll", "crypt32.dll", "bcrypt.dll", "secur32.dll", "netapi32.dll", "iphlpapi.dll", "setupapi.dll", "version.dll", "dwmapi.dll", "uxtheme.dll", "imm32.dll", "winspool.drv", "comctl32.dll", "msvcrt.dll", "ntdll.dll", "api-ms-win-crt-*.dll", "d3d11.dll", "d3d9.dll", "dxgi.dll", "dwrite.dll", "dcomp.dll", "mf.dll", "mfplat.dll", "mfuuid.dll", "propsys.dll", "windowscodecs.dll", "d3d12.dll")]
for m in sorted(set(missing)):
    print("  ", m)

if not missing:
    print("  (无)")
