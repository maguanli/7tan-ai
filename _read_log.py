# -*- coding: utf-8 -*-
# 读取构建日志（GBK 编码）+ 检查构建时间戳与产物
import os

log = r"D:\7tan\7tanAI\dist\rebuild_test_log.txt"
with open(log, "rb") as f:
    data = f.read()

print("=== 日志编码检测 ===")
for enc in ["utf-8", "gbk", "latin-1"]:
    try:
        text = data.decode(enc)
        print(f"  {enc}: OK, {len(text)} 字符")
        break
    except Exception as e:
        print(f"  {enc}: FAIL {e}")

text = data.decode("utf-8", errors="replace")
lines = text.splitlines()
print(f"总行数: {len(lines)}")
print("\n=== 前 20 行 ===")
for l in lines[:20]:
    print(" ", l)
print("\n=== 最后 40 行 ===")
for l in lines[-40:]:
    print(" ", l)

# 检查时间戳
import time
print("\n=== 文件时间 ===")
for p in [log, r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe",
          r"D:\7tan\7tanAI\dist\7tan-editor\_internal"]:
    if os.path.exists(p):
        t = time.localtime(os.path.getmtime(p))
        print(f"  {p}: {time.strftime('%Y-%m-%d %H:%M:%S', t)}")
