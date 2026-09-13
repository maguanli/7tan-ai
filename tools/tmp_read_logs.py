# -*- coding: utf-8 -*-
"""过滤打包版日志中的登录/引导相关行"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = Path(r"C:\7tan-test\7tan-editor\logs")

keys = ("[Login]", "[Onboarding]", "[Wizard]", "launch_app", "主窗口", "启动",
        "ERROR", "WARNING", "segfault", "Traceback", "user_prefs", "UserPrefs")

for name in ("app_2026-08-27.log", "error_2026-08-27.log"):
    f = base / name
    if not f.exists():
        continue
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"===== {name} (共{len(lines)}行) 命中行 =====")
    for i, ln in enumerate(lines, 1):
        if any(k in ln for k in keys):
            print(f"{i:4d}| {ln[:220]}")

for s in base.glob("segfault_*.txt"):
    print(f"\n===== {s.name} =====")
    print(s.read_text(encoding="utf-8", errors="replace")[:2500])
