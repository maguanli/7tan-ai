# -*- coding: utf-8 -*-
"""补充 version.json 中缺失的 1.0.2 条目（与远程一致）"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VER_JSON = Path(r"D:\7tan\7tanAI\website\updates\version.json")
with open(VER_JSON, encoding="utf-8") as f:
    manifest = json.load(f)

v102 = {
    "version": "1.0.2",
    "channel": "stable",
    "platform": "windows",
    "url": "https://www.7tan.com/updates/7tan-editor-free-v1.0.2.zip",
    "md5": "173f424697309ec1d6affe9e9795f2fa",
    "size": 354140370,
    "notes": "1.0.2 更新：修复协议链接点击无反应、侧边栏版本号不同步、删除对话不实时刷新；新增用户协议/隐私政策(登录勾选+关于页入口)；侧边栏新增问题求助/投诉建议入口；对话右上角显示Token；构建脚本自动同步版本号。",
    "release_date": "2026-08-02",
}
versions = [v for v in manifest.get("versions", []) if v.get("version") != "1.0.2"]
versions.append(v102)
manifest["versions"] = sorted(versions, key=lambda v: [int(x) for x in v["version"].split(".")], reverse=True)
with open(VER_JSON, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print("version.json 最终顺序:", [v["version"] for v in manifest["versions"]])
