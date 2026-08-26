"""
截图OCR插件 — 从浏览器截图中识别文字
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="ocr_screenshot",
    description="对当前浏览器页面截图并进行OCR文字识别。用于从图片中提取游戏名称、版本号等信息。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="media",
    requires_browser=True,
)
def ocr_screenshot() -> str:
    """截图并OCR识别"""
    from src.tools.browser_bridge import get_bridge
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"

    # 获取页面文本（已包含可见文字）
    text = bridge.get_page_text(5000)
    title = bridge.get_page_title()

    return f"""📄 OCR 页面内容:

🏷️ 标题: {title}

📝 页面文字:
{text[:3000]}

💡 提示: 如果文字中包含乱码，说明页面使用了图片或特殊字体。
可以使用 auto_screenshot 截图后人工查看。"""
