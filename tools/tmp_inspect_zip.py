# -*- coding: utf-8 -*-
"""检查发布包内的敏感/后台数据：config.yaml、data/users、auth 等"""
import zipfile
from pathlib import Path

zips = sorted(Path("dist/release").glob("*.zip"))
print("发布包:", [z.name for z in zips])

for zp in zips:
    if "free" not in zp.name:
        continue
    print(f"\n===== {zp.name} =====")
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        # 1) config.yaml 内容
        cfg = [n for n in names if n.endswith("config/config.yaml")]
        for n in cfg:
            print(f"--- {n} 前60行 ---")
            content = zf.read(n).decode("utf-8", errors="replace")
            for i, ln in enumerate(content.splitlines()[:60], 1):
                print(f"{i:3d}| {ln}")
        # 2) 敏感目录/文件扫描
        bad_keywords = ("users/", "auth/", "memory/", ".encryption_key", "games.db",
                        "site_7tan", "api_key", "password", "token")
        print("\n--- 可疑条目扫描 ---")
        for n in names:
            low = n.lower()
            if any(k in low for k in bad_keywords):
                info = zf.getinfo(n)
                print(f"  {n}  ({info.file_size}B)")
