# -*- coding: utf-8 -*-
"""验证 novel_writer 插件能否被插件管理器正常加载，工具是否注册进 TOOL_REGISTRY"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.plugins.manager import PluginManager
from src.tools.registry import TOOL_REGISTRY

print("=== 1. 清单检查 ===")
mgr = PluginManager()
manifest = mgr.get_manifest()
info = mgr.get_plugin_info("novel_writer")
print(f"manifest 条目: {'✅ 存在' if info else '❌ 缺失'}")
if info:
    print(f"  名称: {info.get('name')}")
    print(f"  分类: {info.get('category')}  图标: {info.get('icon')}")
    print(f"  工具: {info.get('tools')}")

installed = mgr.get_installed()
print(f"installed 列表: {'✅ 已安装' if 'novel_writer' in installed else '❌ 未安装'}")

print("\n=== 2. 实际加载测试 ===")
mgr._load_plugin("novel_writer", str(ROOT / "data/plugins/novel_writer"))
print("加载调用完成（无异常 = 通过 plugin_guard 白名单校验）")

print("\n=== 3. 工具注册检查 ===")
for tool_name in ("novel_quality_check", "novel_chapter_blueprint"):
    if tool_name in TOOL_REGISTRY:
        t = TOOL_REGISTRY[tool_name]
        print(f"✅ {tool_name} 已注册 | 描述: {t.description[:40]}...")
    else:
        print(f"❌ {tool_name} 未注册！")

print("\n=== 4. 插件市场可见性模拟 ===")
results = mgr._search_local("novel")
for r in results:
    print(f"市场搜索'novel'命中: {r['id']} (installed={r['installed']})")

print("\n🎉 验证完成")
