"""
深度分析插件 — 游戏评测和对比
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="analyze_game",
    description="对一款游戏进行深度分析，生成包含评价、优缺点、玩法特色的结构化报告。用于撰写高质量游戏推荐文章。",
    parameters={
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "description": "游戏名称"},
            "source_text": {"type": "string", "description": "游戏介绍原文（从网页提取）"},
        },
        "required": ["game_name", "source_text"]
    },
    category="analysis",
)
def analyze_game(game_name: str, source_text: str) -> str:
    """游戏分析报告生成"""
    analysis = f"""📊 {game_name} 分析报告

🎮 游戏类型: （从原文中提取游戏类型）
✨ 核心特色: （从原文中提取 3-5 个核心卖点）
👍 优势: （从原文中提取 3 个优势）
⚠️ 注意事项: （如果有缺点或限制，提取 2-3 个）
📱 支持平台: （提取支持的平台信息）
🎨 画面风格: （提取画面/美术风格描述）
💰 收费模式: （提取收费方式）

📝 原始资料:
{source_text[:3000]}

💡 使用上述结构编写一篇专业的游戏推荐文章（200-400字），用 HTML 格式。
"""
    return analysis


@register_tool(
    name="compare_games",
    description="对比两款游戏的差异。用于写竞品对比文章或帮助用户选择游戏。",
    parameters={
        "type": "object",
        "properties": {
            "game1": {"type": "string", "description": "第一款游戏名称"},
            "desc1": {"type": "string", "description": "第一款游戏描述"},
            "game2": {"type": "string", "description": "第二款游戏名称"},
            "desc2": {"type": "string", "description": "第二款游戏描述"},
        },
        "required": ["game1", "game2"]
    },
    category="analysis",
)
def compare_games(game1: str, desc1: str = "", game2: str = "", desc2: str = "") -> str:
    """游戏对比"""
    return f"""⚔️ 游戏对比: {game1} vs {game2}

| 维度 | {game1} | {game2} |
|------|---------|---------|
| 类型 | （待分析） | （待分析） |
| 画面 | （待分析） | （待分析） |
| 玩法 | （待分析） | （待分析） |
| 价格 | （待分析） | （待分析） |
| 评分 | （待分析） | （待分析） |

{game1} 描述: {desc1[:500] if desc1 else '（无）'}
{game2} 描述: {desc2[:500] if desc2 else '（无）'}

💡 基于以上信息，用 AI 推理完成对比表格和推荐。"""


@register_tool(
    name="summarize_reviews",
    description="汇总游戏用户评价。提取正面/负面评价的关键词和主题。",
    parameters={
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "description": "游戏名称"},
            "review_text": {"type": "string", "description": "评价文本（多条评价用换行分隔）"},
        },
        "required": ["game_name", "review_text"]
    },
    category="analysis",
)
def summarize_reviews(game_name: str, review_text: str) -> str:
    """用户评价汇总"""
    return f"""📝 {game_name} 用户评价汇总

原文评价:
{review_text[:3000]}

💡 基于以上评价，总结:
1. 👍 正面关键词（3-5个）
2. 👎 负面关键词（3-5个）
3. ⭐ 综合推荐度（1-5星）
4. 📊 好评率估算

请 AI 自行分析评价内容并生成汇总。"""
