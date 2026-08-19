# -*- coding: utf-8 -*-
import os

targets = ["7tan-editor-v1.0.12.zip", "7tan-web-v1.0.12.zip", "base_library.zip", "piper_windows_amd64.zip"]
roots = [r"D:\7tan\7tanAI", r"D:\7tan\7tanAI\dist", r"D:\7tan\7tanAI\build", r"D:\7tan\7tanAI\output", r"D:\7tan\7tanAI\downloads", r"D:\7tan\7tanAI\backups"]

found = {}
for root in roots:
    if not os.path.isdir(root):
        print("[不存在目录]", root)
        continue
    print("[扫描]", root)
    try:
        items = os.listdir(root)
    except Exception as e:
        print("   listdir 失败:", e)
        continue
    for it in items:
        full = os.path.join(root, it)
        if os.path.isfile(full) and it.lower().endswith('.zip'):
            try:
                size = os.path.getsize(full)
            except Exception:
                size = -1
            found.setdefault(it, []).append((full, size))
            print("   FILE:", full, size)
        elif os.path.isdir(full) and it.lower() in ('dist', 'release', 'build', 'web'):
            try:
                for sub in os.listdir(full):
                    subfull = os.path.join(full, sub)
                    if os.path.isfile(subfull) and sub.lower().endswith('.zip'):
                        size = os.path.getsize(subfull)
                        found.setdefault(sub, []).append((subfull, size))
                        print("   SUBFILE:", subfull, size)
            except Exception as e:
                print("   子目录失败:", full, e)

print("\n=== 汇总 ===")
for fn, paths in found.items():
    print(fn)
    for p, s in paths:
        print("   ", p, s)
