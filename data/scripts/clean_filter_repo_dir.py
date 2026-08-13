# -*- coding: utf-8 -*-
"""删除 .git/filter-repo 残留目录，确保 filter-repo 全新运行"""
import os
import shutil

p = r"D:\7tan\7tanAI\.git\filter-repo"
if os.path.exists(p):
    shutil.rmtree(p, ignore_errors=True)
    print("REMOVED" if not os.path.exists(p) else "REMOVE_FAILED")
else:
    print("MISSING")

# 顺便检查 .git 下是否有其他 filter-repo 相关残留
git_dir = r"D:\7tan\7tanAI\.git"
for name in os.listdir(git_dir):
    if "filter" in name.lower() or "interrupt" in name.lower():
        print("FOUND:", name)
