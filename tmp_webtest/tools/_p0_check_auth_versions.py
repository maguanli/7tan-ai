# -*- coding: utf-8 -*-
"""确认 auth_client 版本并统一为 online_verify 修复版（262,151B）"""
import hashlib
import shutil
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

ROOT = Path(r"D:\7tan\7tanAI")
targets = [
    ROOT / "src" / "security" / "auth_client.pyd",
    ROOT / "src" / "security" / "auth_client_broken.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client_broken.pyd",
    ROOT / "dist" / "7tan-editor" / "_internal" / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "7tan-editor" / "_internal" / "src" / "security" / "auth_client_broken.pyd",
    ROOT / "backups" / "auth_client_new_onlineverify.pyd",
    ROOT / "backups" / "pyd_fix_backup" / "auth_client.pyd.20260802_144323.bak",
]
print("== 现有 auth_client 文件 ==")
for p in targets:
    if p.exists():
        print(f"  {p.stat().st_size:>9}  {md5(p)[:12]}  {p}")
    else:
        print(f"  {'—':>9}  {'—':>12}  {p}  [不存在]")
