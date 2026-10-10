# -*- coding: utf-8 -*-
"""
联网搜索插件 —— 让 AI 搜索互联网获取最新信息

引擎链（国内优先，逐个降级）：Bing(cn) → 百度 → 搜狗 → 360 → DuckDuckGo(海外兜底)

2026-09-27 重写：
  · 引擎逻辑统一收敛到 src/tools/search_engines.py（内置版与本插件共用，避免
    两份实现行为不一致）；
  · 移除 DDG 长达 30s 的卡顿（国内连不通），新增搜狗/360 两个国内可用引擎；
  · 增加结果相关性校验与错误可见性。
"""
import sys
from pathlib import Path

# 注册到工具系统
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.tools.registry import register_tool
from src.tools.search_engines import search_all, format_results


@register_tool(
    name="web_search",
    description="搜索互联网获取最新资讯。用于查找游戏评测、攻略、补丁、新闻等。返回搜索结果摘要。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "num_results": {"type": "integer", "description": "结果数量", "default": 5},
        },
        "required": ["query"]
    },
    category="search",
)
def web_search(query: str, num_results: int = 5) -> str:
    """多引擎搜索：Bing → 百度 → 搜狗 → 360 → DuckDuckGo 自动降级"""
    engine, results, errors, used_q = search_all(query, num_results)
    return format_results(engine, results, errors, used_q, num_results)


@register_tool(
    name="fetch_news",
    description="获取最新游戏行业新闻。用于了解行业动态、新游上线、版本更新等。",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "新闻主题（如：游戏、手游、Steam等）", "default": "游戏"},
            "count": {"type": "integer", "description": "获取条数", "default": 5},
        },
        "required": []
    },
    category="search",
)
def fetch_news(topic: str = "游戏", count: int = 5) -> str:
    """获取最新游戏新闻"""
    return web_search(f"{topic} 最新新闻", num_results=count)
