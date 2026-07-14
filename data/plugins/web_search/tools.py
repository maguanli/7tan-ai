"""
联网搜索插件 — 让 AI 搜索互联网获取最新信息
"""
import sys
from pathlib import Path

# 注册到工具系统
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


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
    """Bing/Google 搜索（免费版用 DuckDuckGo）"""
    try:
        import requests
        # 使用 DuckDuckGo 免费搜索 API
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        data = resp.json()

        results = []
        # Abstract
        if data.get("AbstractText"):
            results.append(f"📝 摘要: {data['AbstractText']}\n  来源: {data.get('AbstractURL', '')}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"🔗 {topic['Text']}\n  URL: {topic.get('FirstURL', '')}")

        if not results:
            # 降级：使用 HTML 搜索链接
            html_url = f"https://html.duckduckgo.com/html/?q={query}"
            html_resp = requests.get(html_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            import re
            links = re.findall(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', html_resp.text)
            for url, title in links[:num_results]:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                results.append(f"🔗 {title_clean}\n  {url}")

        if not results:
            return f"❌ 未找到 '{query}' 的搜索结果"

        return f"🔍 搜索: {query}\n\n" + "\n\n".join(results)

    except ImportError:
        return "❌ requests 库未安装"
    except Exception as e:
        return f"❌ 搜索失败: {e}"


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
    return web_search(f"{topic} 最新新闻 2026", num_results=count)
