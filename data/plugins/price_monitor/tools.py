"""
价格监控插件 — 游戏价格变动追踪
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="check_price",
    description="查询某款游戏在各平台的当前价格。支持 Steam/Epic/TapTap 等平台。",
    parameters={
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "description": "游戏名称"},
        },
        "required": ["game_name"]
    },
    category="monitor",
)
def check_price(game_name: str) -> str:
    """查询游戏价格 — 通过搜索获取"""
    return web_search_internal(f"{game_name} price Steam 价格 多少钱")


@register_tool(
    name="price_alert",
    description="设置游戏价格提醒。当游戏价格降到目标价以下时通知。",
    parameters={
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "description": "游戏名称"},
            "target_price": {"type": "number", "description": "目标价格（元）"},
        },
        "required": ["game_name", "target_price"]
    },
    category="monitor",
)
def price_alert(game_name: str, target_price: float) -> str:
    """设置价格提醒"""
    import json
    alerts_file = Path(ROOT) / "data" / "price_alerts.json"
    alerts = []
    if alerts_file.exists():
        try:
            alerts = json.loads(alerts_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    alerts.append({
        "game": game_name,
        "target": target_price,
        "created_at": __import__('datetime').datetime.now().isoformat(),
    })

    alerts_file.parent.mkdir(parents=True, exist_ok=True)
    alerts_file.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"✅ 已设置价格提醒: {game_name} ≤ ¥{target_price}"


def web_search_internal(query: str) -> str:
    """内部搜索函数"""
    try:
        import requests
        import re
        html_url = f"https://html.duckduckgo.com/html/?q={query}"
        resp = requests.get(html_url, timeout=15,
                           headers={"User-Agent": "Mozilla/5.0"})
        links = re.findall(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
                          resp.text)
        if not links:
            return f"❌ 未找到 '{query}' 的价格信息"

        results = [f"🔍 {query}:"]
        for url, title in links[:5]:
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            results.append(f"  - {title_clean}\n    {url}")
        return "\n".join(results)
    except Exception as e:
        return f"❌ 价格查询失败: {e}"
