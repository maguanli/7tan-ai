# -*- coding: utf-8 -*-
"""列出根目录被 git 跟踪的文件（不含子目录）"""
import subprocess
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

out = subprocess.check_output(
    ["git", "ls-files"], cwd=r"D:\7tan\7tanAI",
    text=True, encoding="utf-8", errors="replace",
)
roots = [f for f in out.splitlines() if "/" not in f]
with open(r"D:\7tan\7tanAI\data\scripts\root_files.txt", "w", encoding="utf-8") as fp:
    fp.write("\n".join(roots))
print("total root tracked files:", len(roots))
