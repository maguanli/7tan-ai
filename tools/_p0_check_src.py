# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

# 1. _build/src/security 状态
sec = Path(r"D:\7tan\7tanAI\dist\_build\src\security")
print("== _build/src/security ==")
for p in sorted(sec.iterdir()):
    print(f"  {p.name} ({p.stat().st_size} B)" if p.is_file() else f"  [DIR] {p.name}")

# 2. src 源里的 .bak / broken 文件（打包会排除 *.bak）
print("\n== src 源中的可疑文件（打包自动排除 *.bak，仅记录） ==")
for p in sorted(Path(r"D:\7tan\7tanAI\src").rglob("*")):
    if p.is_file() and (p.name.endswith((".bak", ".old")) or "broken" in p.name.lower()):
        print(f"  {p.relative_to(Path(r'D:\7tan\7tanAI\src'))}")
