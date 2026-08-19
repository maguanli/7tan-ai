"""
联网搜索工具 — 基于 Bing 搜索，国内直连可用
"""
import re
import json
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.tools.registry import register_tool


# Bing 搜索配置
BING_URL = "https://www.bing.com/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _search_bing(query: str, num_results: int = 5) -> list[dict]:
    """核心：Bing 搜索，返回 [{title, url, snippet}]"""
    params = {"q": query, "count": min(num_results, 20), "setlang": "zh-cn"}
    try:
        resp = requests.get(BING_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        # Bing 搜索结果在 <li class="b_algo"> 中
        for item in soup.select("li.b_algo"):
            title_tag = item.select_one("h2 a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")
            snippet_tag = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= num_results:
                break

        # 降级：如果 .b_algo 没找到，尝试更宽泛的匹配
        if not results:
            for item in soup.select("li h2 a"):
                title = item.get_text(strip=True)
                url = item.get("href", "")
                parent_p = item.find_parent("li")
                snippet = ""
                if parent_p:
                    p_tag = parent_p.find("p")
                    if p_tag:
                        snippet = p_tag.get_text(strip=True)
                if title and url:
                    results.append({"title": title, "url": url, "snippet": snippet})
                if len(results) >= num_results:
                    break

        return results
    except requests.RequestException as e:
        logger.warning(f"Bing 搜索请求失败: {e}")
        return []
    except Exception as e:
        logger.error(f"Bing 搜索解析失败: {e}")
        return []


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
    """搜索互联网"""
    results = _search_bing(query, num_results)
    if not results:
        return "❌ 搜索无结果或请求失败，请稍后重试。"

    lines = [f"🔍 搜索「{query}」结果：\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   🔗 {r['url']}")
        if r.get("snippet"):
            lines.append(f"   📝 {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


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
    query = f"{topic} 最新消息"
    results = _search_bing(query, count)

    if not results:
        return f"❌ 获取「{topic}」新闻失败，请稍后重试。"

    lines = [f"📰 {topic} 最新资讯：\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   🔗 {r['url']}")
        if r.get("snippet"):
            lines.append(f"   📝 {r['snippet']}")
        lines.append("")
    return "\n".join(lines)
