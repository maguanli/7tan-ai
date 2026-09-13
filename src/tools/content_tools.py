"""
内容处理工具 — AI 改写简介、敏感词检查等
"""
from pathlib import Path

from loguru import logger
from .registry import register_tool

# 敏感词列表
_sensitive_words = None


def _load_sensitive_words():
    """加载敏感词列表"""
    global _sensitive_words
    if _sensitive_words is not None:
        return _sensitive_words

    _sensitive_words = set()
    word_files = [
        Path("config/sensitive_words.txt"),
        Path(__file__).parent.parent.parent / "config" / "sensitive_words.txt",
    ]
    for f in word_files:
        if f.exists():
            with open(f, "r", encoding="utf-8") as fp:
                for line in fp:
                    word = line.strip()
                    if word and not word.startswith("#"):
                        _sensitive_words.add(word)
            break
    return _sensitive_words


@register_tool(
    name="check_sensitive_words",
    description="检查文本中是否包含敏感词。发布前必须调用此工具审核内容。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要检查的文本"},
        },
        "required": ["text"]
    },
    category="content",
)
def check_sensitive_words(text: str) -> str:
    """检查敏感词"""
    words = _load_sensitive_words()
    found = []
    for word in words:
        if word and word in text:
            found.append(word)

    if found:
        return f"⚠️ 发现 {len(found)} 个敏感词: {', '.join(found)}"
    return "✅ 未发现敏感词"


@register_tool(
    name="check_content_quality",
    description="检查内容质量：简介长度、截图数量等。",
    parameters={
        "type": "object",
        "properties": {
            "intro": {"type": "string", "description": "简介文本"},
            "screenshot_count": {"type": "integer", "description": "截图数量", "default": 0},
        },
        "required": ["intro"]
    },
    category="content",
)
def check_content_quality(intro: str, screenshot_count: int = 0) -> str:
    """检查内容质量"""
    issues = []
    if len(intro) < 100:
        issues.append(f"简介过短 ({len(intro)}字，最少100字)")
    if screenshot_count < 1:
        issues.append("缺少截图（最少1张）")

    if issues:
        return "⚠️ 内容质量问题:\n  - " + "\n  - ".join(issues)
    return f"✅ 内容质量合格 (简介{len(intro)}字, 截图{screenshot_count}张)"
