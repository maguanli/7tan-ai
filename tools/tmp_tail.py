# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

base = Path(r"C:\7tan-test\7tan-editor\logs")

# 1) error log
for f in base.glob("error_*.log"):
    t = f.read_text(encoding="utf-8", errors="replace")
    print(f"== {f.name} ({len(t)} chars) ==")
    print(t[:4000])

# 2) segfault
for f in base.glob("segfault_*.txt"):
    t = f.read_text(encoding="utf-8", errors="replace")
    print(f"\n== {f.name} ({len(t)} chars) ==")
    print(t[:2500])

# 3) app log 尾部30行（含关闭前的完整上下文）
f = base / "app_2026-08-27.log"
lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
print("\n== app log 尾部30行 ==")
for ln in lines[-30:]:
    print(ln[:230])
