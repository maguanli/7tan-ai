# -*- coding: utf-8 -*-
"""
联网搜索工具（内置版）—— 多引擎自动降级

引擎链（国内优先）：Bing(cn) → 百度 → 搜狗 → 360 → DuckDuckGo(海外兜底)

2026-09-27 重写：
  · 引擎实现统一收敛到 src/tools/search_engines.py，与插件版 data/plugins/web_search
    共用同一份逻辑，避免"谁后注册谁生效"导致行为不一致；
  · 修复原来只走 Bing 单引擎、Bing 一挂就整体失败的问题；
  · 增加结果相关性校验（拦截跑偏结果）与引擎错误可见性。
"""
from src.tools.registry import register_tool
from src.tools.search_engines import (
    search_all,
    format_results,
    normalize_query as _normalize_query,   # 向后兼容：旧调用点仍可 import
)

__all__ = ["web_search", "fetch_news", "_normalize_query"]


@register_tool(
    name="web_search",
    description="搜索互联网获取最新资讯。用于查找游戏评测、攻略、补丁、新闻等。返回搜索结果摘要。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "num_results": {"type": "integer", "description": "结果数量", "default": 5},
        },
        "required": ["query"],
    },
    category="search",
)
def web_search(query: str, num_results: int = 5) -> str:
    """搜索互联网（Bing → 百度 → 搜狗 → 360 → DuckDuckGo）"""
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
        "required": [],
    },
    category="search",
)
def fetch_news(topic: str = "游戏", count: int = 5) -> str:
    """获取最新游戏新闻"""
    return web_search(f"{topic} 最新消息", num_results=count)
