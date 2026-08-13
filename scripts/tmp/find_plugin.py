# -*- coding: utf-8 -*-
import os

# 搜索 novel_writer 插件目录（常见位置）
roots = [r"D:\7tan", r"D:\用户目录", r"G:\AI_Video", r"G:\AI_Tools"]
found = []
for root in roots:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        # 限制深度
        depth = dirpath[len(root):].count(os.sep)
        if depth > 4:
            dirnames[:] = []
            continue
        base = os.path.basename(dirpath)
        if "novel_writer" in base.lower() or "novelwriter" in base.lower():
            found.append(dirpath)
            print("FOUND DIR:", dirpath, "| tools.py:", os.path.isfile(os.path.join(dirpath, "tools.py")))
print("DONE, total:", len(found))
