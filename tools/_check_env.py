# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")

print("== dist\\7tan-editor\\_internal 目录 ==")
internal = ROOT / "dist" / "7tan-editor" / "_internal"
if internal.exists():
    for f in sorted(internal.iterdir())[:30]:
        print("  ", f.name, f.stat().st_size if f.is_file() else "<dir>")

print("\n== _internal 里的 pyd ==")
for f in internal.rglob("*.pyd"):
    print("  ", f.relative_to(internal), f.stat().st_size)

print("\n== dist\\_build 的 config / data 目录 ==")
for sub in ["config", "data", "data/logo", "data/plugins"]:
    p = ROOT / "dist" / "_build" / sub
    print(f"  {'OK ' if p.exists() else 'MISS'} {sub}")
    if p.exists():
        for f in sorted(p.iterdir())[:8]:
            print("      ", f.name)

print("\n== src\\security 下 pyd 导出名复核 ==")
import re
for name in ["auth_client.pyd", "auth_client_new.pyd"]:
    p = ROOT / "src" / "security" / name
    b = p.read_bytes()
    syms = sorted(set(re.findall(rb"PyInit_[A-Za-z0-9_]+", b)))
    print(f"  {name}: {[s.decode() for s in syms]}")
