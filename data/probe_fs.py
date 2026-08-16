# -*- coding: utf-8 -*-
import os

root = r"D:\7tan\7tanAI"
print("getcwd:", os.getcwd())
print("root exists:", os.path.exists(root))
if os.path.isdir(root):
    items = os.listdir(root)
    print("root items (%d):" % len(items))
    for it in sorted(items):
        full = os.path.join(root, it)
        print("  ", it, "DIR" if os.path.isdir(full) else "FILE", os.path.getsize(full) if os.path.isfile(full) else "")
else:
    # 可能 root 本身不存在，看看 D:\ 有什么
    print("D:\\ exists:", os.path.exists(r"D:\\"))
    if os.path.isdir(r"D:\\"):
        for it in sorted(os.listdir(r"D:\\"))[:40]:
            print("  D:\\", it)
