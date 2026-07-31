# -*- coding: utf-8 -*-
"""添加 Defender 排除项 - 结果写文件避免编码问题"""
import subprocess, sys

paths = [
    r"D:\7tan\7tanAI\dist",
    r"D:\7tan\7tanAI\dist\_build\temp",
    r"D:\7tan\7tanAI\dist\_python",
]

log = []
ps = "Add-MpPreference -ExclusionPath @('%s')" % "','".join(paths)
r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                   capture_output=True, timeout=60)
log.append("add rc: %s" % r.returncode)
log.append("add out: %s" % (r.stdout.decode("utf-8", errors="replace").strip()[:500] or "(empty)"))
log.append("add err: %s" % (r.stderr.decode("utf-8", errors="replace").strip()[:800] or "(empty)"))

r2 = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath | Out-String"],
                    capture_output=True, timeout=30)
out2 = r2.stdout.decode("utf-8", errors="replace").strip()
log.append("exclusions: %s" % (out2 or "(none)"))

with open(r"D:\7tan\7tanAI\_excl_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log))
print("written")
