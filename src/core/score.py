"""
评分系统 — 能力值计算模块
根据配置权重计算各维度加权得分，支持自动评估。

维度：
  - AI 模型 (25%): 根据当前配置的模型提供商、模型等级评估
  - 账号等级 (20%): 2026-09-01 开源后不再区分等级，恒为满分
  - 插件/工具 (45%): 已安装插件数量、工具注册数量、品类覆盖度
  - 系统健康 (10%): 磁盘、数据库、网络等

等级划分：
  S: >= 90  卓越
  A: >= 75  优秀
  B: >= 60  良好
  C: >= 40  一般
  D: >= 20  较差
  E: <  20  很差
"""
import shutil
import json
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config.loader import load_config

# ============================================================
# 模型评分映射 — 按提供商和模型等级
# ============================================================

PROVIDER_BASE_SCORE = {
    "deepseek": 85,
    "openai": 90,
    "siliconflow": 70,
    "doubao": 65,
    "mimo": 88,
    "qwen": 85,
    "ollama": 40,
    "custom": 50,
}

MODEL_TIER_BONUS = {
    # 顶级模型 → 加分
    "deepseek-flash": 8,
    "deepseek-reasoner": 12,
    "gpt-4o": 15,
    "gpt-4-turbo": 12,
    "gpt-4o-mini": 8,
    "claude-3.5-sonnet": 15,
    "claude-3-opus": 13,
    "qwen-max": 8,
    "qwen3-max": 15,
    "doubao-pro-32k": 8,
    "mimo-v2.5-pro": 15,
    "llama3": 5,
    "mistral": 5,
}


def get_score_weights() -> dict:
    """从配置文件加载评分权重"""
    config = load_config()
    score_config = config.get("score", {})
    return {
        "ai_model": score_config.get("ai_model", 0.25),
        "account_level": score_config.get("account_level", 0.20),
        "plugins_tools": score_config.get("plugins_tools", 0.45),
        "system_health": score_config.get("system_health", 0.10),
    }


def get_score_grade(score: float) -> str:
    """分数 → 等级"""
    if score >= 90:
        return "S"
    elif score >= 75:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 40:
        return "C"
    elif score >= 20:
        return "D"
    else:
        return "E"


def get_grade_color(grade: str) -> str:
    """等级 → 颜色"""
    colors = {
        "S": "#FFD700",  # 金色
        "A": "#00E676",  # 翠绿
        "B": "#448AFF",  # 蓝色
        "C": "#FFC107",  # 琥珀
        "D": "#FF6D00",  # 橙色
        "E": "#FF1744",  # 红色
    }
    return colors.get(grade, "#888888")


def get_grade_emoji(grade: str) -> str:
    """等级 → 表情"""
    emojis = {
        "S": "👑",
        "A": "⭐",
        "B": "✅",
        "C": "👍",
        "D": "⚠️",
        "E": "❌",
    }
    return emojis.get(grade, "❓")


# ============================================================
# 各维度评估函数
# ============================================================

def evaluate_ai_model() -> float:
    """
    评估 AI 模型维度 (0-100)

    根据配置文件中的模型提供商和模型名称综合评分。
    """
    try:
        config = load_config()
        ai_config = config.get("ai", {})

        # 获取默认模型
        default_model = ai_config.get("default_model", "")
        # 获取提供商
        provider = ai_config.get("provider", "").lower()

        if not default_model and not provider:
            return 0.0

        # 基础分：按提供商
        base = PROVIDER_BASE_SCORE.get(provider, 50)

        # 模型加分
        model_lower = default_model.lower()
        bonus = 0
        for key, val in MODEL_TIER_BONUS.items():
            if key in model_lower:
                bonus = max(bonus, val)

        # 温度/参数合理性加分
        temperature = ai_config.get("temperature", 0.7)
        if 0.3 <= temperature <= 1.0:
            bonus += 2

        # 上下文长度加分
        max_tokens = ai_config.get("max_tokens", 4096)
        if max_tokens >= 32768:
            bonus += 8
        elif max_tokens >= 16384:
            bonus += 5
        elif max_tokens >= 8192:
            bonus += 3

        score = min(base + bonus, 100)
        logger.debug(f"[Score] AI模型评分: provider={provider}, model={default_model}, "
                     f"base={base}, bonus={bonus}, final={score}")
        return float(score)

    except Exception as e:
        logger.warning(f"[Score] AI模型评估失败: {e}")
        return 25.0  # 默认低分


def evaluate_account_level() -> float:
    """
    评估账号等级维度 (0-100)

    2026-09-01 起：7Tan AI 已开源，不再区分 free/pro/enterprise，
    账号等级维度恒为满分（不再产生 ±20 分差异）。
    """
    return 100.0

def evaluate_plugins_tools() -> float:
    """
    评估插件/工具维度 (0-100)

    权重最大(45%)，评估：
    - 已安装插件数量
    - 注册工具数量
    - 工具品类覆盖度（browser/db/file/image/publish/search/monitor等）
    """
    try:
        # --- 已安装插件数 ---
        installed_count = 0
        manifest_path = Path("data/plugins/manifest.json")
        installed_path = Path("data/plugins/installed.json")
        if installed_path.exists():
            try:
                data = json.loads(installed_path.read_text(encoding="utf-8"))
                installed_count = len(data.get("plugins", []))
            except Exception:
                pass

        # 安装得分：每个插件 3 分，最多 40 分
        install_score = min(installed_count * 3, 40)

        # --- 工具注册数量 ---
        tools_count = 0
        categories = set()
        try:
            from src.tools.registry import TOOL_REGISTRY
            tools_count = len(TOOL_REGISTRY)
            for tool in TOOL_REGISTRY.values():
                cat = getattr(tool, 'category', 'unknown')
                categories.add(cat)
        except Exception:
            pass

        # 工具数量得分：每个 1 分，最多 30 分
        tool_count_score = min(tools_count * 1, 30)

        # 品类覆盖得分：每个品类 5 分，最多 30 分
        category_score = min(len(categories) * 5, 30)

        score = install_score + tool_count_score + category_score
        logger.debug(f"[Score] 插件/工具评分: plugins={installed_count}, "
                     f"tools={tools_count}, categories={len(categories)}, final={score}")
        return float(min(score, 100))

    except Exception as e:
        logger.warning(f"[Score] 插件/工具评估失败: {e}")
        return 20.0


def evaluate_system_health() -> float:
    """
    评估系统健康维度 (0-100)

    检查：磁盘空间、数据库连接、网络连通性、配置文件完整性。
    每项 25 分。
    """
    score = 0.0

    try:
        # 1. 磁盘空间 (25分)
        free_gb = shutil.disk_usage(".").free / (1024 ** 3)
        if free_gb > 20:
            score += 25
        elif free_gb > 10:
            score += 20
        elif free_gb > 5:
            score += 15
        elif free_gb > 1:
            score += 8
        else:
            score += 0

        # 2. 数据库连接 (25分)
        try:
            from src.database.db import get_engine
            engine = get_engine()
            engine.connect().close()
            score += 25
        except Exception:
            pass  # 数据库连不上不加分

        # 3. 网络连通性 (25分)
        try:
            import requests
            resp = requests.get("https://www.baidu.com", timeout=5)
            if resp.status_code == 200:
                elapsed_ms = resp.elapsed.total_seconds() * 1000
                if elapsed_ms < 200:
                    score += 25
                elif elapsed_ms < 1000:
                    score += 20
                else:
                    score += 15
        except Exception:
            pass

        # 4. 配置文件完整性 (25分)
        config_path = Path("config/config.yaml")
        if config_path.exists():
            try:
                cfg = load_config()
                required_sections = ["ai", "score", "logging", "security"]
                present = sum(1 for s in required_sections if s in cfg)
                score += (present / len(required_sections)) * 25
            except Exception:
                score += 5  # 文件存在但损坏
        else:
            score += 0

        logger.debug(f"[Score] 系统健康评分: {score}")
        return float(score)

    except Exception as e:
        logger.warning(f"[Score] 系统健康评估失败: {e}")
        return 15.0


# ============================================================
# 能力值计算
# ============================================================

def calculate_composite_score(
    ai_model_score: float = 0,
    account_level_score: float = 0,
    plugins_tools_score: float = 0,
    system_health_score: float = 0,
) -> dict:
    """
    计算加权能力值

    Args:
        ai_model_score:      AI 模型得分 (0-100)
        account_level_score: 账号等级得分 (0-100)
        plugins_tools_score: 插件/工具得分 (0-100)
        system_health_score: 系统健康得分 (0-100)

    Returns:
        dict 包含各维度得分、权重和加权能力值
    """
    weights = get_score_weights()

    weighted_ai = ai_model_score * weights["ai_model"]
    weighted_account = account_level_score * weights["account_level"]
    weighted_plugins = plugins_tools_score * weights["plugins_tools"]
    weighted_health = system_health_score * weights["system_health"]

    total = weighted_ai + weighted_account + weighted_plugins + weighted_health
    grade = get_score_grade(total)

    return {
        "ai_model": {
            "raw_score": ai_model_score,
            "weight": weights["ai_model"],
            "weighted_score": round(weighted_ai, 2),
        },
        "account_level": {
            "raw_score": account_level_score,
            "weight": weights["account_level"],
            "weighted_score": round(weighted_account, 2),
        },
        "plugins_tools": {
            "raw_score": plugins_tools_score,
            "weight": weights["plugins_tools"],
            "weighted_score": round(weighted_plugins, 2),
        },
        "system_health": {
            "raw_score": system_health_score,
            "weight": weights["system_health"],
            "weighted_score": round(weighted_health, 2),
        },
        "composite_score": round(total, 2),
        "grade": grade,
        "grade_emoji": get_grade_emoji(grade),
        "grade_color": get_grade_color(grade),
    }


def auto_evaluate() -> dict:
    """
    一站式自动评估所有维度并返回能力值。

    Returns:
        dict: 同 calculate_composite_score() 的返回格式
    """
    logger.info("[Score] 开始自动评估...")
    return calculate_composite_score(
        ai_model_score=evaluate_ai_model(),
        account_level_score=evaluate_account_level(),
        plugins_tools_score=evaluate_plugins_tools(),
        system_health_score=evaluate_system_health(),
    )


def format_score_report(scores: dict) -> str:
    """格式化评分报告为可读文本"""
    grade = scores.get("grade", "?")
    emoji = scores.get("grade_emoji", "❓")

    lines = [
        f"⚡ 能力值报告  {emoji} {grade}",
        "=" * 40,
        f"  AI 模型:      {scores['ai_model']['raw_score']:>6.1f} × {scores['ai_model']['weight']:.0%} = {scores['ai_model']['weighted_score']:>6.2f}",
        f"  账号等级:     {scores['account_level']['raw_score']:>6.1f} × {scores['account_level']['weight']:.0%} = {scores['account_level']['weighted_score']:>6.2f}",
        f"  插件/工具:    {scores['plugins_tools']['raw_score']:>6.1f} × {scores['plugins_tools']['weight']:.0%} = {scores['plugins_tools']['weighted_score']:>6.2f}",
        f"  系统健康:     {scores['system_health']['raw_score']:>6.1f} × {scores['system_health']['weight']:.0%} = {scores['system_health']['weighted_score']:>6.2f}",
        "-" * 40,
        f"  能力值:     {scores['composite_score']:>6.2f} / 100  ({emoji} {grade})",
    ]
    return "\n".join(lines)


def format_score_brief(scores: dict) -> str:
    """格式化评分摘要（单行，用于 UI 展示）"""
    grade = scores.get("grade", "?")
    emoji = scores.get("grade_emoji", "❓")
    return f"{emoji} {scores['composite_score']:.1f} / 100  ({grade})"
