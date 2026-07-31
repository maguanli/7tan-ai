# -*- coding: utf-8 -*-
"""确认 Defender 状态 + 是否删除 PYZ.pyz"""
import subprocess, os, json

# 1. Defender 实时保护状态
print("=== Defender 实时保护状态 ===")
ps1 = "(Get-MpComputerStatus).RealTimeProtectionEnabled"
try:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps1],
                       capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    print("RealTimeProtectionEnabled:", r.stdout.strip() or r.stderr.strip()[:200])
except Exception as e:
    print("err:", e)

# 2. 排除项（用 Out-String 避免编码问题）
print("\n=== Defender 排除路径 ===")
ps2 = "(Get-MpPreference).ExclusionPath | Out-String -Width 500"
try:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps2],
                       capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    print(r.stdout.strip() if r.stdout.strip() else "(无排除项)")
except Exception as e:
    print("err:", e)

# 3. 检查 backup exe 是否含完整归档（PYZ 内嵌检查）
print("\n=== 备份 exe 与当前 exe 对比 ===")
bak = r"D:\7tan\7tanAI\dist\7tan-editor_backup_周六022608_001946.exe"
cur = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
for name, p in [("当前 exe", cur), ("备份 exe", bak)]:
    if os.path.exists(p):
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            data = f.read()
        # 查找 CArchive 特征: MEI\014\013\012\013\016
        idx = data.find(b"MEI\x0c\x0b\x0a\x0b\x0e")
        idx2 = data.find(b"MEI\x00\x00\x00")
        print(f"{name}: {size} bytes, CArchive头位置={idx}, MEI00={idx2}")

# 4. _internal 里 src 目录完整结构
print("\n=== _internal/src 结构 ===")
src = r"D:\7tan\7tanAI\dist\7tan-editor\_internal\src"
for root, dirs, files in os.walk(src):
    for f in files:
        print("  ", os.path.relpath(os.path.join(root, f), src))
