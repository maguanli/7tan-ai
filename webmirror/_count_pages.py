# -*- coding: utf-8 -*-
import os, json, collections

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
print("EXISTS:", os.path.isdir(TASK))

# 1. 递归数所有文件 + 按扩展名分类
ext_count = collections.Counter()
total_files = 0
html_like = 0
for root, dirs, files in os.walk(TASK):
    for f in files:
        total_files += 1
        e = os.path.splitext(f)[1].lower()
        ext_count[e] += 1
        if e in (".html", ".htm"):
            html_like += 1

print("总文件数(递归):", total_files)
print("html/htm 数:", html_like)
print("扩展名分布 top20:")
for e, c in ext_count.most_common(20):
    print("   ", repr(e), c)

# 2. 顶层目录结构
print("\n顶层内容:")
for name in sorted(os.listdir(TASK)):
    full = os.path.join(TASK, name)
    if os.path.isdir(full):
        n = sum(len(fs) for _, _, fs in os.walk(full))
        print("   [DIR]", name, "->", n, "files")
    else:
        print("   [FILE]", name, os.path.getsize(full), "bytes")
