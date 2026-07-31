# -*- coding: utf-8 -*-
"""同步开发机 src -> dist/_build/src（排除敏感目录）+ 关键文件"""
import os, shutil, hashlib

DEV = r"D:\7tan\7tanAI"
BUILD = r"D:\7tan\7tanAI\dist\_build"
SRC = os.path.join(DEV, "src")
DST = os.path.join(BUILD, "src")

EXCLUDE_DIRS = {"_source_backup", "__pycache__", ".pytest_cache", "temp", ".git"}
EXCLUDE_EXTS = {".pyc", ".pyo"}

copied, skipped = 0, 0
for root, dirs, files in os.walk(SRC):
    # 过滤目录
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    rel = os.path.relpath(root, SRC)
    dst_dir = DST if rel == "." else os.path.join(DST, rel)
    os.makedirs(dst_dir, exist_ok=True)
    for f in files:
        if os.path.splitext(f)[1].lower() in EXCLUDE_EXTS:
            skipped += 1
            continue
        src_f = os.path.join(root, f)
        dst_f = os.path.join(dst_dir, f)
        # 仅在内容变化时复制
        if os.path.exists(dst_f) and os.path.getsize(src_f) == os.path.getsize(dst_f):
            if hashlib.md5(open(src_f, "rb").read()).hexdigest() == hashlib.md5(open(dst_f, "rb").read()).hexdigest():
                skipped += 1
                continue
        shutil.copy2(src_f, dst_f)
        copied += 1

print(f"复制: {copied} 个文件, 跳过(未变化/排除): {skipped}")

# 同步关键文件
for name in ["main.py", "build.spec", "requirements.txt"]:
    s, d = os.path.join(DEV, name), os.path.join(BUILD, name)
    if os.path.exists(s):
        shutil.copy2(s, d)
        print(f"同步: {name}")

# 清理 _build/src 中已不存在的文件（删除开发机已删除的）
def collect(path):
    out = set()
    for root, dirs, files in os.walk(path):
        if any(x in EXCLUDE_DIRS for x in root.split(os.sep)):
            continue
        for f in files:
            if os.path.splitext(f)[1].lower() not in EXCLUDE_EXTS:
                out.add(os.path.relpath(os.path.join(root, f), path))
    return out

dev_set = collect(SRC)
build_set = collect(DST)
stale = build_set - dev_set
for rel in sorted(stale):
    p = os.path.join(DST, rel)
    os.remove(p)
    print(f"清理过期: {rel}")
print(f"清理完成: {len(stale)} 个过期文件")

# 最终校验
import subprocess
r = subprocess.run([os.path.join(DEV, "dist", "_python", "python.exe"),
                    os.path.join(DEV, "_check_sync.py")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout)
