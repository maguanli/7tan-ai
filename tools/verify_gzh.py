# -*- coding: utf-8 -*-
"""验证 gzh_publish 插件注册结果：哈希匹配 + 校验通过 + 可加载 + 工具可调用"""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\7tan\7tanAI")
sys.path.insert(0, str(ROOT))

from src.security.plugin_guard import verify_plugin_file, verify_and_load, load_whitelist

PLUGIN_DIR = ROOT / "data" / "plugins"
WHITELIST = PLUGIN_DIR / "hashes.json"

# 1) 白名单哈希一致性
wl = json.loads(WHITELIST.read_text(encoding="utf-8"))
digest = hashlib.sha256((PLUGIN_DIR / "gzh_publish" / "tools.py").read_bytes()).hexdigest()
print("1) gzh_publish 白名单哈希:", wl["plugins"].get("gzh_publish", "❌ 缺失"))
print("   实际 tools.py 哈希:", digest)
print("   匹配:", wl["plugins"].get("gzh_publish") == digest)

# 2) 整体白名单签名校验（返回结构自适应）
res = load_whitelist(str(WHITELIST))
if isinstance(res, tuple):
    print(f"2) load_whitelist → 返回 {len(res)} 项: {res}")
else:
    print(f"2) load_whitelist → {res}")

# 3) 单插件完整性校验
ok, reason = verify_plugin_file("gzh_publish", PLUGIN_DIR / "gzh_publish" / "tools.py", str(WHITELIST))
print(f"3) verify_plugin_file → ok={ok}, reason={reason}")

# 4) 实际加载 + 工具注册
module = verify_and_load("gzh_publish", str(PLUGIN_DIR / "gzh_publish"), str(WHITELIST))
from src.tools.registry import TOOL_REGISTRY
tools = [n for n in TOOL_REGISTRY if n.startswith("gzh_")]
print(f"4) 加载成功，注册工具: {tools}")

# 5) 工具可调用（安全动作：环境检查，不点屏幕）
r = TOOL_REGISTRY["gzh_env_check"].function()
print("5) gzh_env_check() 输出预览:")
print("   ", r[:200].replace("\n", " | "))
