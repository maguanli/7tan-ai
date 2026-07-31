# -*- coding: utf-8 -*-
"""检查 _build 中 8 个 .pyd 的 DLL 依赖"""
import subprocess, glob, os

OBJDUMP = r"D:\7tan\mingw64\bin\objdump.exe"

for p in sorted(glob.glob(r"D:\7tan\7tanAI\dist\_build\src\security\*.pyd")):
    out = subprocess.run(
        [OBJDUMP, "-p", p],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    dlls = [l.split("DLL Name:")[1].strip() for l in out.splitlines() if "DLL Name:" in l]
    print(os.path.basename(p), "->", dlls)
