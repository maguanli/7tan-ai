# -*- coding: utf-8 -*-
"""检查 images/第1章 内容"""
import os

base = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说', 'images')
ch1 = os.path.join(base, '第1章')
log = []
log.append(f"images: {os.listdir(base)!r}")
if os.path.exists(ch1):
    items = sorted(os.listdir(ch1))
    log.append(f"第1章: {len(items)} 项")
    for it in items:
        p = os.path.join(ch1, it)
        if os.path.isfile(p):
            log.append(f"  {it!r}  {os.path.getsize(p)} bytes")
        else:
            log.append(f"  [DIR] {it!r}")
else:
    log.append("第1章 不存在")

# 全盘搜 ch01_*.png
log.append("")
log.append("=== 搜索 ch01_*.png 文件 ===")
for root, dirs, files in os.walk(os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')):
    for f in files:
        if f.lower().startswith('ch01_') and f.lower().endswith('.png'):
            log.append(f"  {os.path.join(root, f)!r}  {os.path.getsize(os.path.join(root, f))}")

with open(r'D:\7tan\7tanAI\diag_log2.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
print("done", len(log))
