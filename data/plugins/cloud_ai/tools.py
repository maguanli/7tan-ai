"""
Cloud Code 插件 — 复用软件已配置的 AI 进行深度分析
直接使用 config.yaml 中的 API Key 和模型，零配置
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


def _get_client():
    """直接使用软件当前活跃的 AI 配置"""
    from openai import OpenAI
    from src.config.loader import load_config
    config = load_config()
    ai = config.get("ai", {})
    active = ai.get("active", "deepseek")
    cfg = ai.get("configs", {}).get(active, {})
    key = cfg.get("api_key", "")
    url = cfg.get("base_url", "https://api.deepseek.com/v1")
    model = cfg.get("model", "deepseek-chat")
    return OpenAI(api_key=key, base_url=url), model if key else (None, None)


@register_tool(
    name="cloud_analyze",
    description="深度分析模式。用软件当前的AI模型单独调用一次进行深度推理，适合写游戏简介、对比评测等需要仔细思考的任务。",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "分析任务描述"},
            "context": {"type": "string", "description": "参考资料"},
        },
        "required": ["prompt", "context"]
    },
    category="ai",
)
def cloud_analyze(prompt: str, context: str) -> str:
    client, model = _get_client()
    if client is None:
        return f"⚠️ AI未配置，请基于资料完成:\n{prompt}\n\n{context[:3000]}"

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "资深游戏编辑。仔细思考，给出高质量中文回复。"},
                {"role": "user", "content": f"任务：{prompt}\n\n资料：\n{context[:8000]}"},
            ],
            max_tokens=2000, temperature=0.7,
        )
        return f"☁️ 深度分析结果:\n\n{resp.choices[0].message.content}"
    except Exception as e:
        return f"⚠️ 分析失败({e})\n\n{prompt}\n\n{context[:2000]}"


@register_tool(
    name="cloud_write_intro",
    description="用深度分析模式撰写游戏发布简介（HTML格式）。自动提取要点生成专业文案。",
    parameters={
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "description": "游戏名称"},
            "game_info": {"type": "string", "description": "游戏详情（页面提取的文本）"},
        },
        "required": ["game_name", "game_info"]
    },
    category="ai",
)
def cloud_write_intro(game_name: str, game_info: str) -> str:
    prompt = f"为「{game_name}」写150-200字HTML格式发布简介（<p><b><br>标签）。含类型、玩法、画面、特色。吸引人但不夸张。"
    return cloud_analyze(prompt, game_info)
