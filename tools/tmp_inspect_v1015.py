# -*- coding: utf-8 -*-
"""专项检查 v1.0.15 发布包中的敏感数据"""
import zipfile
from pathlib import Path

zp = Path("dist/release/7tan-editor-free-v1.0.15.zip")
with zipfile.ZipFile(zp) as zf:
    names = zf.namelist()
    print(f"总条目: {len(names)}")
    print("顶层结构:", sorted(set(n.split("/")[0] for n in names)))

    # 1) config.yaml 完整内容
    for n in names:
        if n.endswith("config/config.yaml"):
            print(f"\n===== {n} =====")
            content = zf.read(n).decode("utf-8", errors="replace")
            lines = content.splitlines()
            print(f"(共{len(lines)}行)")
            for i, ln in enumerate(lines, 1):
                print(f"{i:3d}| {ln}")

    # 2) 敏感关键词全包扫描
    print("\n===== 敏感扫描 =====")
    for n in names:
        low = n.lower()
        if any(k in low for k in ("site_7tan", "users/", "auth/", "memory/",
                                   ".encryption", "games.db", "sensetime")):
            print(f"  [路径命中] {n}")
    # 内容级扫描：只查小文本文件
    for n in names:
        if n.endswith((".yaml", ".txt", ".json")) and zf.getinfo(n).file_size < 200_000:
            try:
                t = zf.read(n).decode("utf-8", errors="ignore")
            except Exception:
                continue
            hits = []
            if "sk-cPHNvAthZKKzaolF3va5s8MPPGWX3sZM" in t:
                hits.append("sensetime明文KEY")
            if "site_7tan" in t:
                hits.append("site_7tan后台配置")
            if "username: admin" in t:
                hits.append("admin用户名")
            if hits:
                print(f"  [内容命中] {n} -> {hits}")
