# -*- coding: utf-8 -*-
"""启动完整构建（干净参数）"""
import subprocess, sys, os

py = r"D:\7tan\7tanAI\dist\_python\python.exe"
spec = r"D:\7tan\7tanAI\dist\_build\build.spec"
dist = r"D:\7tan\7tanAI\dist"
work = r"D:\7tan\7tanAI\dist\_build\temp"
logf = r"D:\7tan\7tanAI\dist\build_verify_log.txt"

cmd = [py, "-m", "PyInstaller", spec,
       "--distpath", dist,
       "--workpath", work,
       "--noconfirm", "--clean"]

print("CMD:", " ".join(cmd))
with open(logf, "w", encoding="utf-8") as lf:
    p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=r"D:\7tan\7tanAI\dist")
print("PID:", p.pid)
print("已启动，日志:", logf)
