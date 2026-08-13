# -*- coding: utf-8 -*-
"""深度验证：所有 refs（分支+标签）历史中无敏感文件"""
import re

src = r"D:\7tan\7tanAI\data_scripts_all_files_tmp.txt"
sensitive = [
    "games.db", ".encryption_key", ".encryption_salt", "data/users/",
    "data/memory/", ".pyd", ".onnx",
]

with open(src, encoding="utf-8", errors="ignore") as f:
    content = f.read()

lines = set(l.strip() for l in content.splitlines() if l.strip())
print(f"历史中出现过的唯一文件路径数: {len(lines)}")

hits = []
for l in lines:
    low = l.lower()
    if any(p.lower() in low for p in sensitive):
        hits.append(l)

if hits:
    print(f"!!! 发现 {len(hits)} 个敏感路径残留:")
    for h in sorted(hits)[:50]:
        print("  " + h)
else:
    print(">>> 通过: 所有 refs 历史中无任何敏感文件残留")
