# -*- coding: utf-8 -*-
import os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
D = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
print("== 顶层文件 ==")
for x in sorted(os.listdir(D)):
    p = os.path.join(D, x)
    if os.path.isfile(p):
        print("  %-40s %10.1f MB" % (x, os.path.getsize(p) / 1048576))
    else:
        n = sum(len(f) for _, _, f in os.walk(p))
        print("  %-40s <目录> %d 个文件" % (x, n))

# 流水账行数（抽样统计，不全读）
jp = os.path.join(D, "_mirror_queue.ndjson")
if os.path.isfile(jp):
    cnt = 0
    with open(jp, "rb") as f:
        for _ in f:
            cnt += 1
    print("\n流水账 _mirror_queue.ndjson 行数 =", cnt)
