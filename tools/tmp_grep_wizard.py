# -*- coding: utf-8 -*-
"""排查 welcome_wizard 中 _username 的定义与使用"""
import re
from pathlib import Path

src = Path("src/ui/welcome_wizard.py").read_text(encoding="utf-8")
lines = src.splitlines()
print(f"总行数: {len(lines)}")
for i, ln in enumerate(lines, 1):
    if "_username" in ln or "username" in ln:
        print(f"{i:4d}: {ln}")
