# -*- coding: utf-8 -*-
"""修复 rebuild.bat 编码问题：UTF-8 → GBK，移除 chcp 65001"""
import os, shutil

BAT = r"D:\7tan\7tanAI\dist\rebuild.bat"

# 1. 备份原始 UTF-8 版本
bak = BAT + ".utf8.bak"
if not os.path.exists(bak):
    shutil.copy2(BAT, bak)
    print("已备份 UTF-8 原版 ->", bak)
else:
    print("备份已存在:", bak)

# 2. 以 UTF-8 读取
with open(BAT, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
print("原始字符数:", len(content))

# 3. 移除 chcp 65001 行
lines = content.splitlines()
new_lines = [l for l in lines if "chcp 65001" not in l]
content = "\r\n".join(new_lines)
print("移除 chcp 65001 行")

# 4. GBK 编码（不可编码字符替换）
try:
    data = content.encode("gbk")
except UnicodeEncodeError as e:
    print("不可 GBK 字符:", e, "-> 替换")
    data = content.encode("gbk", errors="replace")

# 5. 写回 GBK
with open(BAT, "wb") as f:
    f.write(data)
print("已写回 GBK 编码:", BAT, f"({len(data)} 字节)")

# 6. 语法快速自检：第一行和关键行
with open(BAT, "rb") as f:
    head = f.read(200)
print("文件头:", head[:80])
