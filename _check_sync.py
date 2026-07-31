# -*- coding: utf-8 -*-
"""检查 _build 与开发机源码是否同步"""
import hashlib
import os
import sys
from pathlib import Path

DEV = Path(r"D:\7tan\7tanAI")
BUILD = Path(r"D:\7tan\7tanAI\dist\_build")

def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()

def rel_files(root: Path, exts=(".py", ".yaml", ".txt", ".spec", ".json")):
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in exts:
            if "__pycache__" in p.parts or "_source_backup" in p.parts or "temp" in p.parts:
                continue
            out[str(p.relative_to(root))] = p
    return out

dev_files = rel_files(DEV / "src")
build_files = rel_files(BUILD / "src")

print("=== src 目录文件对比 ===")
only_dev = set(dev_files) - set(build_files)
only_build = set(build_files) - set(dev_files)
print(f"仅开发机有: {len(only_dev)} 个")
for f in sorted(only_dev):
    print(f"  [DEV ONLY] {f}")
print(f"仅 _build 有: {len(only_build)} 个")
for f in sorted(only_build):
    print(f"  [BUILD ONLY] {f}")

print("\n=== 内容不一致文件 ===")
diff_cnt = 0
for rel in sorted(set(dev_files) & set(build_files)):
    d, b = dev_files[rel], build_files[rel]
    if d.stat().st_size != b.stat().st_size or md5(d) != md5(b):
        print(f"  [DIFF] {rel}  dev={d.stat().st_size}B build={b.stat().st_size}B")
        diff_cnt += 1
print(f"共 {diff_cnt} 个文件内容不一致")

# main.py / build.spec / requirements.txt
print("\n=== 关键根文件对比 ===")
for name in ["main.py", "build.spec", "requirements.txt"]:
    d = DEV / name
    b = BUILD / name
    if d.exists() and b.exists():
        same = md5(d) == md5(b)
        print(f"  {name}: {'一致' if same else '不一致!'}")
    else:
        print(f"  {name}: 开发机={'有' if d.exists() else '无'} _build={'有' if b.exists() else '无'}")

# 检查 _build/src/security 的 pycache
print("\n=== _build/src/security 内容 ===")
sec = BUILD / "src" / "security"
for p in sorted(sec.iterdir()):
    print(f"  {p.name} ({p.stat().st_size}B)")
