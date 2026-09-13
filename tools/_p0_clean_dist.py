# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

root = Path(r"D:\7tan\7tanAI\dist")
hits = []
for p in sorted(root.rglob("*")):
    if not p.is_file():
        continue
    n = p.name.lower()
    if "broken" in n or n.endswith((".bak", ".old")) or n.startswith(("test_", "_fix", "_check", "_tmp")):
        hits.append(p)

print(f"共 {len(hits)} 个调试残留文件:")
for p in hits:
    print(f"  {p.relative_to(root)}  ({p.stat().st_size} B)")

# 直接删除（P0 要求清理）
for p in hits:
    p.unlink()
    print(f"  [DEL] {p.relative_to(root)}")
print("清理完成")
