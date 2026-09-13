"""
AI Prompt 模板管理 — 数据库为唯一真相源，文件为缓存/回退
"""
from pathlib import Path
from datetime import datetime
from loguru import logger


# 默认 Prompt 模板（仅首次初始化时使用，之后以数据库为准）
DEFAULT_PROMPTS = {
    "system": """## 🧠 你是谁
你是 7Tan 的全栈开发者 AI，代号 CodeLion。核心能力：写代码、发布游戏、浏览网页、系统维护。

## 💡 核心原则
- **解决问题优先** — 先给方案再给解释，不废话
- **直接行动** — 能写代码就写代码，能用工具就用工具，别只说"你可以这样"
- **遇到困难想办法** — 不轻易说做不到，尝试替代方案
- **诚实不消极** — 做不到就说做不到，但给出替代方案

## ⛔ 硬性规则
- 🚫 禁止 `eval()` / `exec()` 用户输入
- 🚫 禁止 SQL 拼接，只用参数化查询
- 🚫 未经用户明确同意，禁止调用 self_restart / self_rebuild / self_modify
- ⚠️ 网络请求必须设超时，文件路径用 pathlib

## 📋 发布流程（严格顺序）
1. use_source_browser → browse_page
2. find_download_links + get_page_images
3. download_file + compress_image
4. oss_upload
5. check_content_quality + check_sensitive_words
6. use_admin_browser → publish_to_7tan
7. db_save_resource

## 🔒 Pro 等级
- **free**：可用的工具列表不含自修改类工具，不主动建议使用
- **pro**：拥有全部工具
- free 用户要求修改配置/重启等操作 → 提示升级

## 🌐 浏览与下载
- 列表页先 scroll_down 再 browse_page
- 下载前 check_disk
- LOGO/截图先下载到本地再发布
""",

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


def _get_prompts_dir() -> Path:
    """获取 prompts 目录（兼容不同运行模式）"""
    return Path("data/prompts")


def get_prompt(prompt_type: str) -> str:
    """
    获取指定类型的 prompt 模板。
    优先级：数据库 > 文件 > 默认模板
    """
    # 1. 优先从数据库读取
    try:
        from ..database.db import get_prompt_from_db
        row = get_prompt_from_db(prompt_type)
        if row and row.get("content", "").strip():
            return row["content"]
    except Exception as e:
        logger.debug(f"从数据库读取 prompt '{prompt_type}' 失败: {e}")

    # 2. 回退到文件
    custom_file = _get_prompts_dir() / f"{prompt_type}.txt"
    if custom_file.exists():
        content = custom_file.read_text(encoding="utf-8")
        if content.strip():
            return content

    # 3. 最后回退到默认模板
    return DEFAULT_PROMPTS.get(prompt_type, "")


def save_prompt(prompt_type: str, template: str):
    """保存自定义 prompt 模板（仅文件，供外部直接调用）"""
    prompts_dir = _get_prompts_dir()
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / f"{prompt_type}.txt").write_text(template, encoding="utf-8")


def list_prompts() -> dict:
    """列出所有可用的 prompt 模板"""
    prompts = {}
    # 从数据库获取
    try:
        from ..database.db import get_all_prompts
        db_prompts = get_all_prompts()
        for p in db_prompts:
            prompts[p["prompt_type"]] = {
                "source": "database",
                "updated_at": p.get("updated_at", ""),
                "char_count": p.get("char_count", 0),
            }
    except Exception:
        pass

    # 补充默认模板
    for ptype in DEFAULT_PROMPTS:
        if ptype not in prompts:
            prompts[ptype] = {
                "source": "default",
                "custom": (_get_prompts_dir() / f"{ptype}.txt").exists(),
            }
    return prompts


def update_prompt(prompt_type: str, new_template: str, reason: str = ""):
    """
    更新提示词模板。
    数据库为唯一真相源，文件为缓存/回退。
    """
    # 1. 写入数据库（主存储）
    try:
        from ..database.db import upsert_prompt
        result = upsert_prompt(prompt_type, new_template, reason)
        logger.info(f"💾 提示词已写入数据库: {prompt_type} ({result.get('action')}) — {reason}")
    except Exception as e:
        logger.error(f"❌ 写入数据库失败: {e}")
        # 如果数据库写入失败，仍尝试写文件作为紧急备份
        _sync_to_file(prompt_type, new_template, reason)
        raise RuntimeError(f"提示词更新失败：数据库写入错误 — {e}")

    # 2. 同步到文件（缓存/回退）
    _sync_to_file(prompt_type, new_template, reason)


def _sync_to_file(prompt_type: str, content: str, reason: str = ""):
    """将提示词同步到文件（缓存）"""
    try:
        prompts_dir = _get_prompts_dir()
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompts_dir / f"{prompt_type}.txt"
        prompt_file.write_text(content, encoding="utf-8")
        if reason:
            log_path = prompts_dir / f"{prompt_type}.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {reason}\n")
        logger.debug(f"📄 提示词已同步到文件: {prompt_type}.txt")
    except Exception as e:
        logger.warning(f"⚠️ 同步到文件失败: {e}")
