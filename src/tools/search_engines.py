# -*- coding: utf-8 -*-
"""
联网搜索引擎集合 —— 多引擎自动降级（国内优先）

2026-09-27 重写，修复以下问题：
  1. 原引擎链 Bing → 百度 → DuckDuckGo：DDG 在国内连不通，且连接超时长达 30s，
     一旦前两个引擎失败就白等半分钟。→ 移除 DDG 主链路，改为极短超时兜底。
  2. 新增两个实测可用的国内引擎：搜狗、360，作为真正的兜底。
  3. Bing 改用 cn.bing.com（实测 0.68s，比 www.bing.com 的 1.2s 更快更稳）。
  4. 新增结果相关性校验：命中查询关键词才采纳，避免返回无关内容
     （曾出现搜「王牌战争」被返回成综艺「王牌对王牌」的情况）。
  5. 引擎错误不再被静默吞掉，通过 errors 列表上抛，便于排查。
  6. 增加整体时间预算（默认 25s），全部引擎都失败时也不会无限等待。
"""
import re
import time

import requests
from loguru import logger

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:  # pragma: no cover
    _HAS_BS4 = False

# 单引擎超时 (连接超时, 读取超时)
TIMEOUT = (5, 10)
# 整体时间预算：超过这个秒数不再尝试后续引擎
TOTAL_BUDGET = 25.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _soup(html: str):
    return BeautifulSoup(html, "html.parser") if _HAS_BS4 else None


def _txt(node) -> str:
    return node.get_text(strip=True) if node else ""


# --------------------------------------------------------------------------
# 查询归一化：把口语化 query 收敛成核心关键词
# --------------------------------------------------------------------------
def normalize_query(query: str) -> str:
    """把口语 query 归一化成核心关键词（去除人称+能愿动词/疑问/语气词），
    避免 Bing 把「你会写脚本吗」降级成单字「你」的结果。"""
    q = (query or "").strip()
    if not q:
        return ""
    for _ in range(3):
        old = q
        q = re.sub(r"(?:你|您|我|我们|你们|咱们|人家)(?:会不会|能不能|可不可以|会|能|可以|知道|认识|了解|想|想要|需要)(?:不)?", "", q)
        q = re.sub(r"^(?:你|您|我|我们|你们|咱们|人家)", "", q)
        q = re.sub(r"^(?:会|能|可以|想|想要|需要|会不会|能不能|可不可以)", "", q)
        q = re.sub(r"(?:会不会|能不能|可不可以)", "", q)
        q = re.sub(r"^(?:你能帮我|你可以帮我|帮我找一下|帮我查一下|帮我搜一下|帮我查查|帮我|麻烦你|麻烦|请你|请|给我|替我|查一下|搜一下|找一下|搜索一下|查询一下|搜索|查找|看看|请问|问一下|我想知道|我想问|告诉我|介绍一下|推荐一下|给我推荐|想知道|问下)", "", q)
        q = re.sub(r"[？?。！!，,、；;：:]+$", "", q)
        q = re.sub(r"(?<!什)(吗|呢|么|啊|呀|吧|哦|哈|呗|啦|咯|喔)+$", "", q)
        q = re.sub(r"^(?:什么是|是什么|是谁|为什么|为啥|为何|怎么样|怎么|如何|是不是|有没有|有哪些|哪里|哪儿|多少|几点|几号|干嘛|干吗)", "", q)
        q = q.strip(" ？?。，,、 ")
        if q == old:
            break
    q = re.sub(r"\s+", " ", q).strip(" ？?。，,、 ")
    q = q.replace("有多少", "有几")  # Bing 对「有几」检索更敏感，能命中数量答案
    return q if len(q.replace(" ", "")) >= 2 else ""


# --------------------------------------------------------------------------
# 相关性校验
# --------------------------------------------------------------------------
def _terms(query: str) -> list:
    """把查询拆成用于相关性判断的词元（长度 >= 2 的连续片段）。"""
    parts = re.split(r"[\s,，、。？?！!：:；;（）()【】\[\]/|]+", query or "")
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2:
            out.append(p)
    return out


def is_relevant(query: str, results: list) -> bool:
    """结果里至少命中一半查询词元（单/双词元时命中 1 个即可），才算相关。

    用来拦掉「搜王牌战争却返回王牌对王牌」这类跑偏结果。
    """
    terms = _terms(query)
    if not terms or not results:
        return True
    blob = " ".join(
        f"{r.get('title', '')} {r.get('snippet', '')}" for r in results
    ).lower()
    hits = sum(1 for t in terms if t.lower() in blob)
    need = 1 if len(terms) <= 2 else max(2, len(terms) // 2)
    return hits >= need


# --------------------------------------------------------------------------
# 各引擎实现（统一返回 [{title, url, snippet}]）
# --------------------------------------------------------------------------
def search_bing(query: str, num_results: int = 5) -> list:
    """Bing 搜索（走 cn.bing.com，国内更快）"""
    resp = requests.get(
        "https://cn.bing.com/search",
        params={"q": query, "count": min(num_results, 20), "setlang": "zh-cn"},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = _soup(resp.text)
    results = []
    if soup is not None:
        for item in soup.select("li.b_algo"):
            a = item.select_one("h2 a")
            if not a:
                continue
            snippet = _txt(item.select_one(".b_caption p") or item.select_one(".b_lineclamp2"))
            url = a.get("href", "")
            if a.get_text(strip=True) and url:
                results.append({"title": a.get_text(strip=True), "url": url, "snippet": snippet})
            if len(results) >= num_results:
                break
        if not results:  # 宽泛降级
            for a in soup.select("li h2 a"):
                url = a.get("href", "")
                if a.get_text(strip=True) and url:
                    results.append({"title": a.get_text(strip=True), "url": url, "snippet": ""})
                if len(results) >= num_results:
                    break
    else:  # 无 bs4 用正则
        for m in re.finditer(r'<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', resp.text):
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and m.group(1):
                results.append({"title": title, "url": m.group(1), "snippet": ""})
            if len(results) >= num_results:
                break
    return results


def search_baidu(query: str, num_results: int = 5) -> list:
    """百度搜索"""
    resp = requests.get(
        "https://www.baidu.com/s",
        params={"wd": query, "rn": min(num_results, 20)},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = _soup(resp.text)
    results = []
    if soup is not None:
        for item in soup.select("div.result, div.c-container"):
            a = item.select_one("h3 a")
            if not a:
                continue
            snippet = _txt(
                item.select_one(".c-abstract")
                or item.select_one("[class*=content-right]")
                or item.select_one("span")
            )
            url = a.get("href", "")
            if a.get_text(strip=True) and url:
                results.append({"title": a.get_text(strip=True), "url": url, "snippet": snippet[:200]})
            if len(results) >= num_results:
                break
    else:
        for m in re.finditer(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text):
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and m.group(1):
                results.append({"title": title, "url": m.group(1), "snippet": ""})
            if len(results) >= num_results:
                break
    return results


def search_sogou(query: str, num_results: int = 5) -> list:
    """搜狗搜索"""
    resp = requests.get(
        "https://www.sogou.com/web",
        params={"query": query},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = _soup(resp.text)
    results = []
    if soup is None:
        return results
    for item in soup.select("div.vrwrap, div.rb"):
        a = item.select_one("h3 a") or item.select_one("a")
        if not a:
            continue
        snippet = _txt(
            item.select_one(".str_info")
            or item.select_one(".text-layout")
            or item.select_one("p")
        )
        url = a.get("href", "")
        if not url.startswith("http"):
            continue
        title = a.get_text(strip=True)
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet[:200]})
        if len(results) >= num_results:
            break
    return results


def search_360(query: str, num_results: int = 5) -> list:
    """360 搜索（so.com）"""
    resp = requests.get(
        "https://www.so.com/s",
        params={"q": query},
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = _soup(resp.text)
    results = []
    if soup is None:
        return results
    for item in soup.select("li.res-list, div.res-list"):
        a = item.select_one("h3 a")
        if not a:
            continue
        snippet = _txt(item.select_one("p.res-desc") or item.select_one(".res-desc") or item.select_one("p"))
        url = a.get("href", "")
        if url.startswith("/"):
            url = "https://www.so.com" + url
        title = a.get_text(strip=True)
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet[:200]})
        if len(results) >= num_results:
            break
    return results


def search_ddg(query: str, num_results: int = 5) -> list:
    """DuckDuckGo（海外兜底，国内通常连不通 → 用极短超时，避免拖慢）"""
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=HEADERS, timeout=(3, 5),
    )
    resp.raise_for_status()
    results = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text):
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if title and m.group(1):
            results.append({"title": title, "url": m.group(1), "snippet": ""})
        if len(results) >= num_results:
            break
    return results


# 引擎链：国内优先，逐个尝试；任一「有结果且相关」即返回
ENGINES = [
    ("Bing", search_bing),
    ("百度", search_baidu),
    ("搜狗", search_sogou),
    ("360", search_360),
    ("DuckDuckGo", search_ddg),
]


# --------------------------------------------------------------------------
# 对外主入口
# --------------------------------------------------------------------------
def search_all(query: str, num_results: int = 5):
    """按引擎链依次搜索。

    Returns:
        (engine_name, results, errors, used_query)
        engine_name: 命中的引擎名（""=全部失败）
        results:     [{title, url, snippet}]
        errors:      ["Bing: Timeout", ...] 便于排查
        used_query:  实际用于搜索的（归一化后）查询
    """
    used_query = normalize_query(query) or (query or "").strip()
    errors = []
    low_rel_fallback = None
    started = time.time()

    for name, fn in ENGINES:
        if time.time() - started > TOTAL_BUDGET:
            errors.append(f"{name}: 超出总时间预算")
            break
        try:
            results = fn(used_query, num_results)
        except requests.RequestException as e:
            errors.append(f"{name}: 连接失败({type(e).__name__})")
            logger.warning(f"搜索引擎 {name} 请求失败: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {type(e).__name__}")
            logger.warning(f"搜索引擎 {name} 解析失败: {e}")
            continue

        if not results:
            errors.append(f"{name}: 无结果")
            continue

        if is_relevant(used_query, results):
            return name, results, errors, used_query

        # 结果与查询不相关：记下来当最后兜底，但继续试下一个引擎
        errors.append(f"{name}: 结果相关性低")
        if low_rel_fallback is None:
            low_rel_fallback = (name, results)

    if low_rel_fallback is not None:
        return low_rel_fallback[0] + "(低相关)", low_rel_fallback[1], errors, used_query
    return "", [], errors, used_query


def format_results(engine: str, results: list, errors: list, used_query: str, num_results: int = 5) -> str:
    """把搜索结果格式化成给 AI 看的文本（引擎错误附在末尾，便于排查）。"""
    if not results:
        detail = ("；".join(errors)) if errors else "未知原因"
        return f"❌ 搜索失败：所有引擎均不可用或无结果（{detail}）。请检查网络后重试。"

    lines = [f"🔍 搜索「{used_query}」（来源：{engine}）：\n"]
    for i, r in enumerate(results[:num_results], 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   🔗 {r['url']}")
        if r.get("snippet"):
            lines.append(f"   📝 {r['snippet'][:200]}")
        lines.append("")
    if errors:
        lines.append(f"（其他引擎状态：{'；'.join(errors)}）")
    return "\n".join(lines)
