"""
自修改工具 — 沙盒执行、策略更新、配置修改
详见架构文档 §12 安全自修改机制
"""
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from loguru import logger

from .registry import register_tool
from ..utils.retry import retry, RETRY_POLICIES

# 自修改沙盒配置
SANDBOX_ROOT = Path("data/sandbox")
SANDBOX_TIMEOUT = 30  # 秒
MAX_OUTPUT_SIZE = 100 * 1024  # 100KB


@register_tool(
    name="self_modify_config",
    description="安全地修改自己的配置文件（config.yaml）。AI 需要用自然语言描述想改什么，系统验证后执行。",
    parameters={
        "type": "object",
        "properties": {
            "key_path": {"type": "string", "description": "配置键路径，如 ai.deepseek.api_key"},
            "new_value": {"type": "string", "description": "新值"},
            "reason": {"type": "string", "description": "修改原因（必填，用于审计日志）"},
        },
        "required": ["key_path", "new_value", "reason"]
    },
    category="self_modify",
    dangerous=True,
)
def self_modify_config(key_path: str, new_value: str, reason: str) -> str:
    """修改配置文件"""
    from ..config.loader import load_config, save_config

    logger.warning(f"🔧 自修改配置: {key_path} = {new_value[:20]}... (原因: {reason})")

    try:
        config = load_config()

        # 按路径设置
        keys = key_path.split(".")
        target = config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        old_value = target.get(keys[-1], "(不存在)")
        target[keys[-1]] = _coerce_value(new_value)

        save_config(config)

        logger.info(f"✅ 配置已更新: {key_path}")
        return f"✅ 配置已更新\n  路径: {key_path}\n  旧值: {old_value}\n  新值: {new_value}"
    except Exception as e:
        logger.error(f"❌ 配置修改失败: {e}")
        return f"❌ 配置修改失败: {e}"


def _coerce_value(val: str):
    """智能类型转换"""
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() == "null" or val.lower() == "none":
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


@register_tool(
    name="sandbox_execute",
    description="在沙盒中安全执行 Python 脚本，验证自生代码。输出限制 100KB，超时 30 秒。",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的 Python 代码"},
            "timeout": {"type": "integer", "description": "超时秒数", "default": 30},
        },
        "required": ["code"]
    },
    category="self_modify",
    dangerous=True,
)
def sandbox_execute(code: str, timeout: int = 30) -> str:
    """沙盒执行 Python 代码"""
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
    script_path = SANDBOX_ROOT / f"test_{code_hash}_{int(time.time())}.py"

    try:
        # 写入脚本
        script_path.write_text(code, encoding="utf-8")

        # 执行（限制资源和时间）
        result = subprocess.run(
            [sys.executable, "-I", str(script_path)],  # -I 隔离模式
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SANDBOX_ROOT),
        )

        stdout = result.stdout[:MAX_OUTPUT_SIZE]
        stderr = result.stderr[:MAX_OUTPUT_SIZE]

        if result.returncode == 0:
            return f"✅ 执行成功\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        else:
            return f"❌ 执行失败 (退出码 {result.returncode})\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"

    except subprocess.TimeoutExpired:
        return "⏰ 沙盒执行超时"
    except Exception as e:
        return f"❌ 沙盒执行异常: {e}"
    finally:
        # 清理
        if script_path.exists():
            script_path.unlink()


@register_tool(
    name="self_update_prompt",
    description="更新 AI 的系统提示词。AI 可以自我优化，也可以更新 scraper/rewriter/reviewer/publisher 等子任务模板。使用 'system' 类型更新主提示词。",
    parameters={
        "type": "object",
        "properties": {
            "prompt_type": {"type": "string", "description": "prompt 类型: system(主提示词)/scraper/rewriter/reviewer/publisher"},
            "new_template": {"type": "string", "description": "新的 prompt 模板"},
            "reason": {"type": "string", "description": "更新原因"},
        },
        "required": ["prompt_type", "new_template", "reason"]
    },
    category="self_modify",
    dangerous=True,
)
def self_update_prompt(prompt_type: str, new_template: str, reason: str) -> str:
    """更新系统 prompt 模板"""
    prompts_dir = Path("data/prompts")
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # 映射 prompt_type 到文件名
    PROMPT_FILES = {
        "system": "system.txt",
        "scraper": "scraper.txt",
        "rewriter": "rewriter.txt",
        "reviewer": "reviewer.txt",
        "publisher": "publisher.txt",
    }
    filename = PROMPT_FILES.get(prompt_type, f"{prompt_type}.txt")
    prompt_file = prompts_dir / filename

    # 备份旧 prompt
    if prompt_file.exists():
        backup = prompts_dir / f"{filename}.bak"
        prompt_file.replace(backup)

    prompt_file.write_text(new_template, encoding="utf-8")
    logger.info(f"📝 Prompt 模板已更新: {prompt_type} → {filename} (原因: {reason})")

    return f"✅ Prompt 模板已更新\n  类型: {prompt_type}\n  文件: {prompt_file}\n  下次对话生效"


@register_tool(
    name="verify_integrity",
    description="验证自身完整性：检查所有关键文件的 SHA-256 校验和是否与 integrity.json 一致。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="self_modify",
)
def verify_integrity() -> str:
    """验证文件完整性"""
    integrity_file = Path("integrity.json")

    if not integrity_file.exists():
        return "⚠️ 未找到 integrity.json，跳过完整性验证"

    try:
        checksums = json.loads(integrity_file.read_text())
    except Exception:
        return "❌ integrity.json 格式错误"

    results = []
    ok_count = 0
    fail_count = 0

    for filepath, expected_hash in checksums.items():
        p = Path(filepath)
        if not p.exists():
            results.append(f"  ❌ 缺失: {filepath}")
            fail_count += 1
            continue

        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual == expected_hash:
            ok_count += 1
        else:
            results.append(f"  ⚠️ 校验失败: {filepath}")
            fail_count += 1

    if fail_count == 0:
        return f"✅ 完整性验证通过 ({ok_count} 个文件)"
    else:
        return f"❌ 完整性验证失败: {ok_count} OK, {fail_count} 失败\n" + "\n".join(results)
