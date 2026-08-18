# -*- coding: utf-8 -*-
"""注册 sunzi 孙子兵法插件：installed.json + manifest.json"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PLUGIN_DIR = Path(r"D:\7tan\7tanAI\data\plugins")

# 1) installed.json 添加 sunzi
inst_file = PLUGIN_DIR / "installed.json"
data = json.loads(inst_file.read_text(encoding="utf-8"))
if "sunzi" not in data["plugins"]:
    data["plugins"].append("sunzi")
inst_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("installed.json 插件数:", len(data["plugins"]), "| 含 sunzi:", "sunzi" in data["plugins"])

# 2) manifest.json 添加 sunzi 条目
man_file = PLUGIN_DIR / "manifest.json"
man = json.loads(man_file.read_text(encoding="utf-8"))
ids = [p.get("id") for p in man]
if "sunzi" not in ids:
    man.append({
        "id": "sunzi",
        "name": "孙子兵法",
        "version": "1.0.0",
        "author": "7tanAI Team",
        "type": "builtin",
        "category": "知识",
        "description": "孙子兵法智慧：兵法问答、决策推演、篇章查询、每日兵法。接入独立知识库项目，先谋后动、避实击虚、知彼知己。",
        "tools": ["sunzi_ask", "sunzi_strategy", "sunzi_chapter", "sunzi_daily"],
        "icon": "⚔️",
    })
man_file.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
print("manifest.json 插件数:", len(man), "| 含 sunzi:", "sunzi" in [p.get("id") for p in man])

print("✅ sunzi 插件注册完成")
