# -*- coding: utf-8 -*-
"""修复 novel_writer 插件未注册问题：补齐 manifest.json / installed.json / hashes.json"""
import json
import shutil
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "data" / "plugins"
MANIFEST = PLUGIN_DIR / "manifest.json"
INSTALLED = PLUGIN_DIR / "installed.json"
HASHES = PLUGIN_DIR / "hashes.json"

# 0. 备份
for f in (MANIFEST, INSTALLED, HASHES):
    if f.exists():
        bak = f.with_suffix(f.suffix + ".bak_before_novel_fix")
        shutil.copy2(f, bak)
        print(f"备份: {bak.name}")

# 1. manifest.json 添加 novel_writer 条目
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
ids = {p.get("id") for p in manifest}
if "novel_writer" not in ids:
    manifest.append({
        "id": "novel_writer",
        "name": "小说写作工坊（番茄方向）",
        "version": "0.1.0",
        "author": "AI Self-Evolution",
        "type": "custom",
        "category": "写作",
        "description": "按《番茄官方写作方法论手册》实现的高质量小说写作套件：①质检引擎 novel_quality_check（8大维度：章节长度/章末钩子/AI痕迹/对话比例/段落节奏/系统面板/引号规范/敏感词）；②章节生成器 novel_chapter_blueprint（黄金节奏点5拍骨架+章末钩子公式）。支持生成→质检→修改闭环。",
        "tools": ["novel_quality_check", "novel_chapter_blueprint"],
        "icon": "📖"
    })
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ manifest.json 已添加 novel_writer")
else:
    print("ℹ️ manifest.json 已有 novel_writer")

# 2. installed.json 添加 novel_writer
installed = json.loads(INSTALLED.read_text(encoding="utf-8"))
plugins = installed.get("plugins", [])
if "novel_writer" not in plugins:
    plugins.append("novel_writer")
    INSTALLED.write_text(json.dumps(installed, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ installed.json 已添加 novel_writer")
else:
    print("ℹ️ installed.json 已有 novel_writer")

# 3. 检查磁盘插件 hash 与现有白名单的差异（防误伤）
try:
    old_hashes = json.loads(HASHES.read_text(encoding="utf-8")).get("plugins", {})
except Exception:
    old_hashes = {}

diff = []
for pkg in sorted(PLUGIN_DIR.iterdir()):
    if not pkg.is_dir():
        continue
    tools = pkg / "tools.py"
    if not tools.exists():
        continue
    digest = __import__("hashlib").sha256(tools.read_bytes()).hexdigest()
    old = old_hashes.get(pkg.name)
    if old is not None and old != digest:
        diff.append(pkg.name)
if diff:
    print(f"⚠️ 注意：以下插件 tools.py 与现有白名单不一致（重签后会被覆盖为新值）: {diff}")
else:
    print("ℹ️ 所有已注册插件 hash 与白名单一致，无异常")

print("\n✅ 修复脚本执行完毕，下一步运行 gen_plugin_hashes.py 重新生成白名单签名")
