"""
AI Prompt 模板管理
"""
from pathlib import Path


# 默认 Prompt 模板
DEFAULT_PROMPTS = {
    "scraper": """你是一个资源情报专家，负责从网页内容中发现游戏和软件资源。

你需要从页面中提取以下信息：
- 标题 (title)
- 版本号 (version)
- 下载链接 (download_url)
- 简介描述 (intro)
- 平台/语言/分类
- LOGO 图片 URL
- 截图 URL 列表

请以 JSON 格式返回结果。只提取确定的信息，不要编造。""",

    "rewriter": """你是一个资深游戏编辑，请将以下资源信息改写为7坛风格。

7坛风格特点：
- 保留原资源的所有关键信息
- 语气活泼但不轻浮
- 标题吸引人但不过分夸张
- 简介包括：特色功能、更新内容、使用说明
- 适当使用 emoji（每段1-2个）
- 字数 300-800 字

原始信息：
{original_info}

请输出改写的标题和简介。""",

    "reviewer": """你是内容审核员，检查以下发布内容是否符合规范：

检查项：
1. 是否有敏感词（政治、色情、暴力）
2. 标题是否恰当（30 字以内）
3. 简介是否足够详细（300 字以上）
4. 截图是否清晰可用
5. 下载链接是否有效
6. 标签是否合理

内容：
{content}

请以 JSON 返回审核结果：{"pass": true/false, "issues": [...], "suggestions": [...]}""",

    "publisher": """你是一个发布助手，帮助将资源发布到7坛网站。

当前需要发布的资源：
{resource}

请确认以下信息无误后，执行发布操作。如有问题请先修正。""",
}


def get_prompt(prompt_type: str) -> str:
    """获取指定类型的 prompt 模板（优先读取自定义文件）"""
    custom_file = Path(f"data/prompts/{prompt_type}.txt")
    if custom_file.exists():
        return custom_file.read_text(encoding="utf-8")
    return DEFAULT_PROMPTS.get(prompt_type, "")


def save_prompt(prompt_type: str, template: str):
    """保存自定义 prompt 模板"""
    prompts_dir = Path("data/prompts")
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / f"{prompt_type}.txt").write_text(template, encoding="utf-8")


def list_prompts() -> dict:
    """列出所有可用的 prompt 模板"""
    prompts = {}
    for ptype in DEFAULT_PROMPTS:
        prompts[ptype] = {
            "default": DEFAULT_PROMPTS[ptype][:100] + "...",
            "custom": Path(f"data/prompts/{ptype}.txt").exists(),
        }
    return prompts


def update_prompt(prompt_type: str, new_template: str, reason: str = ""):
    """更新提示词模板（保存自定义版本并记录原因）"""
    prompts_dir = Path("data/prompts")
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = prompts_dir / f"{prompt_type}.txt"
    prompt_file.write_text(new_template, encoding="utf-8")
    if reason:
        log_path = prompts_dir / f"{prompt_type}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now().isoformat()}] {reason}\n")
