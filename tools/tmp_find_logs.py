# -*- coding: utf-8 -*-
"""查找打包版运行日志，诊断引导窗口问题"""
import pathlib

candidates = [
    pathlib.Path(r"dist/7tan-editor/logs"),
    pathlib.Path(r"D:/用户目录/下载"),
    pathlib.Path(r"D:/用户目录/下载/新建文件夹 123"),
    pathlib.Path(r"C:/Users/Administrator/Downloads"),
    pathlib.Path(r"C:/Users/Administrator/Desktop"),
]

for root in candidates:
    if not root.exists():
        print(f"[MISS] {root} 不存在")
        continue
    hits = []
    for p in root.rglob("app_2026*.log"):
        hits.append(p)
        if len(hits) >= 8:
            break
    # 也找打包目录特征（7tan-editor.exe / data/users）
    exe_hits = list(root.rglob("7tan-editor.exe"))[:3]
    users_hits = list(root.rglob("users"))[:3]
    print(f"[DIR ] {root}")
    for h in hits:
        print(f"   LOG  {h}  ({h.stat().st_size}B, mtime={h.stat().st_mtime})")
    for h in exe_hits:
        print(f"   EXE  {h}")
    for h in users_hits:
        try:
            files = list(h.glob('*.json'))
            print(f"   USERS_DIR {h} -> {[(f.name, f.stat().st_size) for f in files]}")
        except Exception as e:
            print(f"   USERS_DIR {h} err {e}")
