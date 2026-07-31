# -*- coding: utf-8 -*-
"""检查 exe 时间戳、构建痕迹、备份文件"""
import os, time

def ts(p):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p)))
    except Exception:
        return "N/A"

print("=== 关键文件时间戳 ===")
for p in [
    r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe",
    r"D:\7tan\7tanAI\dist\7tan-editor_backup_周六022608_001946.exe",
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PYZ.pyz",
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\python312.dll",
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PyQt6\Qt6\bin\Qt6WebEngineCore.dll",
    r"D:\7tan\7tanAI\dist\build_verify_log.txt",
]:
    print(f"  {ts(p)}  {os.path.getsize(p)/1024/1024 if os.path.exists(p) else '缺失':.1f}MB  {os.path.basename(p)}")

print("\n=== dist 下日志文件 ===")
for f in os.listdir(r"D:\7tan\7tanAI\dist"):
    if "log" in f.lower() or "build" in f.lower():
        p = os.path.join(r"D:\7tan\7tanAI\dist", f)
        print(f"  {ts(p)}  {os.path.getsize(p)/1024:.1f}KB  {f}")

print("\n=== _build 目录结构（构建痕迹）===")
bb = r"D:\7tan\7tanAI\dist\_build"
for name in sorted(os.listdir(bb)):
    p = os.path.join(bb, name)
    print("  ", name, "<DIR>" if os.path.isdir(p) else f"{os.path.getsize(p)/1024:.1f}KB")

print("\n=== _build\\temp 是否存在（PyInstaller 工作目录）===")
temp = os.path.join(bb, "temp")
if os.path.isdir(temp):
    entries = os.listdir(temp)
    print("  存在，", len(entries), "个条目:", entries[:10])
else:
    print("  不存在")
