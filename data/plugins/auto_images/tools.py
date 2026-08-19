"""
自动配图插件 — 智能截图和 LOGO 提取
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="auto_screenshot",
    description="对当前页面自动截取高质量截图。用于获取游戏详情页的预览图。",
    parameters={
        "type": "object",
        "properties": {
            "count": {"type": "integer", "description": "截图张数", "default": 3},
        },
        "required": []
    },
    category="media",
    requires_browser=True,
)
def auto_screenshot(count: int = 3) -> str:
    """自动截图当前页面"""
    from src.tools.browser_bridge import get_bridge
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"

    import os
    save_dir = Path(ROOT) / "data" / "screenshots"
    save_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i in range(count):
        path = save_dir / f"auto_screenshot_{i+1}.png"
        result = bridge.screenshot(str(path))
        results.append(f"  📸 截图 {i+1}: {path}")

    return "✅ 自动截图完成:\n" + "\n".join(results)


@register_tool(
    name="extract_logo",
    description="从当前页面自动识别并下载 LOGO/图标图片。用于获取游戏图标。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="media",
    requires_browser=True,
)
def extract_logo() -> str:
    """提取页面 LOGO"""
    from src.tools.browser_bridge import get_bridge
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"

    images = bridge.get_page_images(50)
    logos = [img for img in images if any(k in str(img).lower() for k in ['logo', 'icon', 'avatar', '头像'])]

    if not logos:
        # 取最小的几张图片做 LOGO 候选
        logos = sorted(images, key=lambda x: x.get('width', 9999) * x.get('height', 9999))[:3]

    if not logos:
        return "❌ 未找到 LOGO 图片"

    import os
    import requests
    save_dir = Path(ROOT) / "downloads" / "logos"
    save_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, logo in enumerate(logos[:3]):
        src = logo.get('src', '')
        if not src or src.startswith('data:'):
            continue
        try:
            resp = requests.get(src, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            ext = src.split('.')[-1].split('?')[0] or 'png'
            path = save_dir / f"logo_{i+1}.{ext}"
            path.write_bytes(resp.content)
            results.append(f"  🎨 LOGO {i+1}: {path} ({len(resp.content)} 字节)")
        except Exception as e:
            results.append(f"  ❌ 下载失败: {src[:60]} - {e}")

    if not results:
        return "❌ LOGO 下载全部失败"

    return "✅ LOGO 提取完成:\n" + "\n".join(results)
