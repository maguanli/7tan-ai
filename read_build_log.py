# -*- coding: utf-8 -*-
"""读 build_log.txt 找被占用文件"""
import os

p = r"D:\7tan\7tanAI\dist\build_log.txt"
if not os.path.exists(p):
    print("build_log.txt 不存在")
    raise SystemExit

with open(p, "rb") as f:
    data = f.read()
print("大小:", len(data), "字节")

# 尝试 GBK 解码
text = data.decode("gbk", errors="replace")

# 找错误行
print("\n=== 含 '无法' / '占用' / 'Error' / 'error' 的行 ===")
for line in text.splitlines():
    low = line.lower()
    if any(k in low for k in ["无法", "占用", "error", "denied", "access", "fail", "locked", "被"]):
        print(" ", line[:300])

print("\n=== 末尾 30 行 ===")
for line in text.splitlines()[-30:]:
    print(" ", line[:300])
