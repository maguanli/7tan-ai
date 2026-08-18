# -*- coding: utf-8 -*-
"""验证 sunzi 插件注册结果：哈希匹配 + 校验通过 + 可加载"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\7tan\7tanAI")
sys.path.insert(0, str(ROOT))

from src.security.plugin_guard import verify_plugin_file, verify_and_load

PLUGIN_DIR = ROOT / "data" / "plugins"
WHITELIST = PLUGIN_DIR / "hashes.json"

# 1) 哈希一致性
wl = json.loads(WHITELIST.read_text(encoding="utf-8"))
digest = __import__("hashlib").sha256((PLUGIN_DIR / "sunzi" / "tools.py").read_bytes()).hexdigest()
print("1) sunzi 白名单哈希:", wl["plugins"].get("sunzi", "❌ 缺失"))
print("   实际 tools.py 哈希:", digest)
print("   匹配:", wl["plugins"].get("sunzi") == digest)

# 2) 完整性校验
ok, reason = verify_plugin_file("sunzi", PLUGIN_DIR / "sunzi" / "tools.py", str(WHITELIST))
print(f"2) verify_plugin_file → ok={ok}, reason={reason}")

# 3) 实际加载 + 工具注册
module = verify_and_load("sunzi", str(PLUGIN_DIR / "sunzi"), str(WHITELIST))
from src.tools.registry import TOOL_REGISTRY
tools = [n for n in TOOL_REGISTRY if n.startswith("sunzi_")]
print(f"3) 加载成功，注册工具: {tools}")

# 4) 工具可调用（本地知识，不依赖 LLM/网络）
r = TOOL_REGISTRY["sunzi_chapter"].function("谋攻", include_modern=False)
print("4) sunzi_chapter('谋攻') 输出预览:")
print("   ", r[:120].replace("\n", " | "))
