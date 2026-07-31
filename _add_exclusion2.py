# -*- coding: utf-8 -*-
"""添加 Defender 排除项（修复编码问题）"""
import subprocess

paths = [
    r"D:\7tan\7tanAI\dist",
    r"D:\7tan\7tanAI\dist\_build\temp",
    r"D:\7tan\7tanAI\dist\_python",
]

ps = "Add-MpPreference -ExclusionPath @('%s')" % "','".join(paths)
r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                   capture_output=True, timeout=60, encoding="utf-8", errors="replace")
out = (r.stdout or b"").decode("utf-8", errors="replace") if isinstance(r.stdout, bytes) else (r.stdout or "")
err = (r.stderr or b"").decode("utf-8", errors="replace") if isinstance(r.stderr, bytes) else (r.stderr or "")
print("add rc:", r.returncode)
print("add out:", out.strip()[:500] or "(empty)")
print("add err:", err.strip()[:500] or "(empty)")

r2 = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath | Out-String"],
                    capture_output=True, timeout=30, encoding="utf-8", errors="replace")
out2 = (r2.stdout or "").strip()
print("exclusions:", out2 or "(none)")
