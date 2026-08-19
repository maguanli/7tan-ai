# -*- coding: utf-8 -*-
"""列出 zip 中可能含用户数据的目录，便于精确过滤"""
import zipfile, os
from collections import Counter

ZIPS = [
    r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.13.zip",
    r"D:\7tan\7tanAI\dist\release\7tan-web-v1.0.13.zip",
]

DATA_HINTS = ("/data/", "/logs/", "/backups/", "/output/", "/recordings/", "/uploads/",
              "/screenshots/", "/ocr_work/", "/downloads/", "/tmp", "/cache", "/.venv/")

for zp in ZIPS:
    print("=" * 60)
    print(os.path.basename(zp))
    z = zipfile.ZipFile(zp)
    names = z.namelist()
    # 顶层目录统计
    tops = Counter(n.split("/")[0] for n in names)
    print("顶层:", dict(tops))
    # 数据类路径
    hits = sorted(set(n for n in names if any(h in n.lower() for h in DATA_HINTS)))
    print(f"数据类路径 {len(hits)} 条:")
    for h in hits[:100]:
        print("  ", h)
    z.close()
print("完成")
