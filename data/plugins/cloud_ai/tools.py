"""
Cloud Code 插件 — 接入云端 AI 增强推理能力
支持 OpenAI GPT-4o-mini 等模型，自动降级到本地 DeepSeek
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


def _get_cloud_client():
    """获取云端 AI 客户端（OpenAI 兼容）"""
    try:
        from openai import OpenAI
        from src.config.loader import load_config
        config = load_config()
        cloud_cfg = config.get("plugins", {}).get("cloud_ai", {})
        api_key = cloud_cfg.get("api_key", "") or config.get("ai", {}).get("configs", {}).get("deepseek", {}).get("api_key", "")
        base_url = cloud_cfg.get("base_url", "https://api.openai.com/v1")
        model = cloud_cfg.get("model", "gpt-4o-mini")
        if not api_key:
            return None, None
        return OpenAI(api_key=api_key, base_url=base_url), model
    except Exception:
        return None, None


@register_tool(
    name="cloud_analyze",
    description="使用云端 AI（GPT-4o-mini）进行深度分析。比本地模型更聪明，用于复杂任务如写游戏简介、分析评测、对比游戏。失败时自动降级。",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "分析任务描述"},
            "context": {"type": "string", "description": "相关上下文资料"},
        },
        "required": ["prompt", "context"]
    },
    category="ai",
)
def cloud_analyze(prompt: str, context: str) -> str:
    """云端 AI 分析 — 用更聪明的模型处理复杂任务"""
    client, model = _get_cloud_client()
    if client is None:
        return f"⚠️ 云端 AI 未配置（在 config.yaml 的 plugins.cloud_ai 中设置 API Key）\n\n请基于以下资料完成任务：\n{prompt}\n\n资料：\n{context[:3000]}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的游戏编辑，擅长分析游戏特点、撰写专业评测和简介。用中文回复。"},
                {"role": "user", "content": f"任务：{prompt}\n\n参考资料：\n{context[:8000]}"},
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        result = response.choices[0].message.content
        return f"☁️ 云端 AI 分析结果 ({model}):\n\n{result}"
    except Exception as e:
        return f"⚠️ 云端 AI 调用失败 ({e})，请基于资料自行分析：\n{prompt}\n\n资料：\n{context[:2000]}"


@register_tool(
    name="cloud_write_intro",
    description="使用云端 AI 撰写游戏发布简介（HTML格式）。自动从游戏信息中提取要点，生成专业、吸引人的介绍文案。",
    parameters={
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "description": "游戏名称"},
            "game_info": {"type": "string", "description": "游戏详情（从页面提取的文本）"},
            "features": {"type": "string", "description": "游戏特色/亮点", "default": ""},
        },
        "required": ["game_name", "game_info"]
    },
    category="ai",
)
def cloud_write_intro(game_name: str, game_info: str, features: str = "") -> str:
    """用云端 AI 写游戏简介"""
    prompt = f"为游戏「{game_name}」写一段约 150-200 字的发布简介，用 HTML 格式（<p>段落、<b>加粗、<br>换行）。包含游戏类型、核心玩法、画面风格、特色亮点。语言生动吸引人，不要夸大。"
    if features:
        prompt += f"\n特色亮点：{features}"
    return cloud_analyze(prompt, game_info)
