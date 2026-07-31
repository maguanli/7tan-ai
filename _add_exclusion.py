# -*- coding: utf-8 -*-
"""添加 Defender 排除项（需要管理员权限）"""
import subprocess, sys

paths = [
    r"D:\7tan\7tanAI\dist",
    r"D:\7tan\7tanAI\dist\_build\temp",
    r"D:\7tan\7tanAI\dist\_python",
]

print("=== 尝试添加 Defender 排除项 ===")
ps = "Add-MpPreference -ExclusionPath @('%s')" % "','".join(paths)
r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                   capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
print("stdout:", r.stdout.strip() or "(空)")
print("stderr:", r.stderr.strip()[:1000] if r.stderr.strip() else "(空)")
print("returncode:", r.returncode)

# 验证
r2 = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath | Out-String"],
                    capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
print("\n=== 当前排除项 ===")
print(r2.stdout.strip() if r2.stdout.strip() else "(无排除项)")
