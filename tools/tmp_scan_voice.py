# -*- coding: utf-8 -*-
"""查 _save_voice_gender 的调用方与关闭应用的相关逻辑"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

src = Path("src/ui/chat_page.py").read_text(encoding="utf-8")
lines = src.splitlines()
print(f"chat_page.py 总行数: {len(lines)}")
for i, ln in enumerate(lines, 1):
    if any(k in ln for k in ("_save_voice_gender", "_load_voice_gender",
                             ".close()", "QApplication.quit", "games.db")):
        print(f"{i:4d}: {ln.rstrip()[:170]}")

print("\n== 全项目搜索 _save_voice_gender 调用 ==")
for p in Path("src").rglob("*.py"):
    t = p.read_text(encoding="utf-8", errors="ignore")
    for i, ln in enumerate(t.splitlines(), 1):
        if "_save_voice_gender" in ln and "def _save_voice_gender" not in ln:
            print(f"{p}:{i}: {ln.strip()[:150]}")
