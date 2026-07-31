# -*- coding: utf-8 -*-
"""_internal 完整条目 + GBK 读 build_verify_log"""
import os

internal = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"
names = sorted(os.listdir(internal))
print(f"=== _internal 共 {len(names)} 个条目 ===")
for n in names:
    p = os.path.join(internal, n)
    if os.path.isdir(p):
        print(f"  [DIR] {n}")
    else:
        print(f"        {n} ({os.path.getsize(p)/1024:.0f}KB)")

print("\n=== 检查 PYZ.pyz ===")
pyz = os.path.join(internal, "PYZ.pyz")
print("  PYZ.pyz 存在:", os.path.exists(pyz))

print("\n=== build_verify_log.txt (GBK, 末尾 50 行) ===")
p = r"D:\7tan\7tanAI\dist\build_verify_log.txt"
with open(p, "rb") as f:
    data = f.read()
text = data.decode("gbk", errors="replace")
print("  总行数:", text.count("\n"), "大小:", len(data))
print("\n".join(text.splitlines()[-50:]))
