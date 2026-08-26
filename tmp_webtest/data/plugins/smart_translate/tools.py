"""
智能翻译插件 — 中英文自动翻译
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="translate_text",
    description="将英文文本翻译为中文。用于翻译游戏介绍、Steam商店描述等。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要翻译的英文文本"},
        },
        "required": ["text"]
    },
    category="language",
)
def translate_text(text: str) -> str:
    """简单翻译 — 使用免费 API"""
    if not text or len(text) < 2:
        return text

    # 快速判断是否已是中文
    import re
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    if cn_chars > len(text) * 0.3:
        return text  # 已经是中文

    try:
        import requests
        # 使用免费翻译 API (Google Translate 非官方)
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": text[:5000],  # 限制长度
        }
        resp = requests.get(url, params=params, timeout=15,
                           headers={"User-Agent": "Mozilla/5.0"})
        result = resp.json()
        translated = ""
        for part in result[0]:
            if part[0]:
                translated += part[0]
        return translated if translated else text
    except Exception as e:
        return f"⚠️ 翻译失败，保留原文: {e}\n\n{text}"
