# -*- coding: utf-8 -*-
import os
p = r"D:\7tan\7tanAI\dist\build_verify_log.txt"
data = open(p, "rb").read()
text = data.decode("utf-8", errors="replace")
# 输出到文件避免 GBK 问题
with open(r"D:\7tan\7tanAI\_build_err.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("written", len(text))
