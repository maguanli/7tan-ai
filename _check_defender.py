# -*- coding: utf-8 -*-
"""检查杀毒软件是否删除 PYZ.pyz + Defender 排除项"""
import os, subprocess, json

# 1. Defender 排除项
print("=== Windows Defender 排除项 ===")
try:
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath | ConvertTo-Json"],
        capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    print("stdout:", r.stdout[:2000] if r.stdout else "(空)")
    print("stderr:", r.stderr[:500] if r.stderr else "")
except Exception as e:
    print("无法获取:", e)

# 2. Defender 检测历史（最近威胁）
print("\n=== Defender 最近检测 ===")
try:
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-MpThreatDetection | Select-Object -First 5 -Property InitialDetectionTime,Resources | Format-List"],
        capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    print(r.stdout[:3000] if r.stdout else "(无检测记录)")
    print(r.stderr[:500] if r.stderr else "")
except Exception as e:
    print("无法获取:", e)

# 3. dist 里有没有 pyc 散落（noarchive 模式特征）
print("\n=== dist/7tan-editor/_internal 根目录 .pyc ===")
internal = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"
pycs = [f for f in os.listdir(internal) if f.endswith(".pyc")]
print(pycs if pycs else "(无散落 pyc)")

# 4. temp 目录看看有没有残留的完整产物
print("\n=== _build/temp 内容 ===")
temp = r"D:\7tan\7tanAI\dist\_build\temp"
if os.path.exists(temp):
    for f in sorted(os.listdir(temp))[:30]:
        print("  ", f)
else:
    print("  (不存在)")
