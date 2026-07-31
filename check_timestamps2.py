# -*- coding: utf-8 -*-
"""检查构建痕迹"""
import os, time

def ts(p):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p)))
    except Exception:
        return "N/A"

print("=== 关键文件时间戳 ===")
for p in [
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PYZ.pyz",
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\python312.dll",
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PyQt6\Qt6\bin\Qt6WebEngineCore.dll",
    r"D:\7tan\7tanAI\dist\build_verify_log.txt",
]:
    if os.path.exists(p):
        print(f"  {ts(p)}  {os.path.getsize(p)/1024/1024:.1f}MB  {os.path.basename(p)}")

print("\n=== _build 目录结构 ===")
bb = r"D:\7tan\7tanAI\dist\_build"
for name in sorted(os.listdir(bb)):
    p = os.path.join(bb, name)
    tag = "<DIR>" if os.path.isdir(p) else f"{os.path.getsize(p)/1024:.1f}KB"
    print("  ", name, tag)

print("\n=== _build\\temp 是否存在 ===")
temp = os.path.join(bb, "temp")
if os.path.isdir(temp):
    print("  存在,", len(os.listdir(temp)), "个条目:", os.listdir(temp)[:10])
else:
    print("  不存在")

print("\n=== build_verify_log.txt 内容（末尾 40 行）===")
p = r"D:\7tan\7tanAI\dist\build_verify_log.txt"
if os.path.exists(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print("".join(lines[-40:]))
