# -*- coding: utf-8 -*-
"""筛选 git 跟踪的敏感文件清单"""
import os

list_file = r"D:\7tan\7tanAI\data_scripts_git_list_tmp.txt"
out_file = r"D:\7tan\7tanAI\data\scripts\sensitive_git_files.txt"

patterns = [
    "games.db", ".encryption", "users/", ".pyd", ".onnx",
    "memory/", ".key", ".db", "token", "secret", "credential",
]

with open(list_file, encoding="utf-8", errors="ignore") as f:
    lines = [l.strip() for l in f if l.strip()]

matched = []
for l in lines:
    low = l.lower()
    if any(p.lower() in low for p in patterns):
        matched.append(l)

with open(out_file, "w", encoding="utf-8") as f:
    f.write("\n".join(matched))

print(f"TOTAL_TRACKED={len(lines)}")
print(f"SENSITIVE_MATCHED={len(matched)}")
for m in matched[:120]:
    print("  " + m)
