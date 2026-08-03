"""
联网搜索插件 — 让 AI 搜索互联网获取最新信息
多引擎自动降级：Bing(国内直连) → 百度(国内) → DuckDuckGo(海外)
"""
import re
import sys
from pathlib import Path

# 注册到工具系统
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

TIMEOUT = 10  # 每个引擎超时秒数（快速失败，避免长时间卡顿）

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def _soup(html: str):
    return BeautifulSoup(html, "html.parser") if _HAS_BS4 else None


def _search_bing(query: str, num_results: int = 5) -> list[dict]:
    """Bing 搜索（国内直连）"""
    import requests
    resp = requests.get(
        "https://www.bing.com/search",
        params={"q": query, "count": min(num_results, 20), "setlang": "zh-cn"},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results = []
    soup = _soup(resp.text)
    if soup is not None:
        for item in soup.select("li.b_algo"):
            title_tag = item.select_one("h2 a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")
            snippet_tag = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title and url:
                results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= num_results:
                break
        if not results:  # 宽泛降级
            for item in soup.select("li h2 a"):
                title = item.get_text(strip=True)
                url = item.get("href", "")
                if title and url:
                    results.append({"title": title, "url": url, "snippet": ""})
                if len(results) >= num_results:
                    break
    else:  # 无 bs4 时用正则
        for m in re.finditer(r'<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', resp.text):
            url, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and url:
                results.append({"title": title, "url": url, "snippet": ""})
            if len(results) >= num_results:
                break
    return results


def _search_baidu(query: str, num_results: int = 5) -> list[dict]:
    """百度搜索（国内）"""
    import requests
    resp = requests.get(
        "https://www.baidu.com/s",
        params={"wd": query, "rn": min(num_results, 20)},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    results = []
    soup = _soup(resp.text)
    if soup is not None:
        for item in soup.select("div.result, div.c-container"):
            title_tag = item.select_one("h3 a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")
            snippet_tag = item.select_one(".c-abstract") or item.select_one(".content-right_8Zs40") or item.select_one("span")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title and url:
                results.append({"title": title, "url": url, "snippet": snippet[:200]})
            if len(results) >= num_results:
                break
    else:  # 正则降级
        for m in re.finditer(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text):
            url, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and url:
                results.append({"title": title, "url": url, "snippet": ""})
            if len(results) >= num_results:
                break
    return results


def _search_duckduckgo(query: str, num_results: int = 5) -> list[dict]:
    """DuckDuckGo HTML 搜索（海外 fallback，最后兜底）"""
    import requests
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text):
        url, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if title and url:
            results.append({"title": title, "url": url, "snippet": ""})
        if len(results) >= num_results:
            break
    return results


# 引擎链：国内优先，逐个尝试，任一成功即返回
_ENGINES = [
    ("Bing", _search_bing),
    ("百度", _search_baidu),
    ("DuckDuckGo", _search_duckduckgo),
]


def _search_all(query: str, num_results: int = 5) -> tuple[str, list[dict]]:
    """按顺序尝试所有引擎，返回 (引擎名, 结果列表)"""
    import requests
    errors = []
    for name, fn in _ENGINES:
        try:
            results = fn(query, num_results)
            if results:
                return name, results
            errors.append(f"{name}: 无结果")
        except requests.RequestException as e:
            errors.append(f"{name}: 连接失败({type(e).__name__})")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}")
    return "", []


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
    """多引擎搜索：Bing → 百度 → DuckDuckGo 自动降级"""
    engine, results = _search_all(query, num_results)
    if not results:
        return ("❌ 搜索失败：所有搜索引擎均不可用（Bing/百度/DuckDuckGo 连接超时或无结果）。"
                "请检查网络连接后重试。")

    lines = [f"🔍 搜索「{query}」（来源：{engine}）：\n"]
    for i, r in enumerate(results[:num_results], 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   🔗 {r['url']}")
        if r.get("snippet"):
            lines.append(f"   📝 {r['snippet'][:200]}")
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
        "required": []
    },
    category="search",
)
def fetch_news(topic: str = "游戏", count: int = 5) -> str:
    """获取最新游戏新闻"""
    return web_search(f"{topic} 最新新闻 2026", num_results=count)
