"""
自修改工具 — 沙盒执行、策略更新、配置修改、自主重建
详见架构文档 §12 安全自修改机制
"""
import copy
import hashlib
import json
import os
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
def _get_project_root():
    """获取可靠的项目根目录 — 兼容 PyInstaller 打包和开发模式"""
    root = Path(__file__).resolve().parent.parent.parent  # src/tools/xxx.py → 项目根

    # 在 PyInstaller 打包后，__file__ 可能指向 _internal/.../xxx.py
    # 此时 parent.parent.parent 得到的是 _internal/，而非真正的项目根
    # 判断标准：真正的项目根一定有 build.bat，而 _internal/ 只有 config（被打包进去了）
    if (root / "build.bat").exists():
        return root

    # 否则从 sys.executable 推断：exe 在 dist/7tan-editor/，项目根在 ../../../
    exe_dir = Path(sys.executable).parent
    candidates = [
        exe_dir.parent.parent.parent,  # dist/7tan-editor → ../../.. → 项目根
        exe_dir.parent.parent,         # dist/7tan-editor → ../.. → dist 上级
        exe_dir.parent,                # dist/7tan-editor → .. → dist（备用）
        exe_dir,                       # exe 自身目录（备用）
    ]
    for c in candidates:
        if (c / "build.bat").exists():
            logger.info(f"🔍 检测到项目根: {c}")
            return c

    # 最后回退
    logger.warning(f"⚠️ 无法定位项目根，使用: {root}")
    return root


PROJECT_ROOT = _get_project_root()

# 自修改沙盒配置
SANDBOX_ROOT = PROJECT_ROOT / "data/sandbox"
SANDBOX_TIMEOUT = 30  # 秒
MAX_OUTPUT_SIZE = 100 * 1024  # 100KB

# 缓存真实 Python 解释器路径
_REAL_PYTHON = None


def _find_real_python() -> str:
    """找到真正的 Python 解释器（而非 PyInstaller exe）"""
    global _REAL_PYTHON
    if _REAL_PYTHON and Path(_REAL_PYTHON).exists():
        return _REAL_PYTHON

    is_frozen = getattr(sys, 'frozen', False)

    if not is_frozen:
        # 开发环境：直接用当前 Python
        _REAL_PYTHON = sys.executable
        return _REAL_PYTHON

    # ===== PyInstaller 打包环境：需要找到真正的 Python =====

    # 候选1：_base_executable（某些 PyInstaller 版本支持）
    base_exe = getattr(sys, '_base_executable', None)
    if base_exe and Path(base_exe).exists():
        _REAL_PYTHON = base_exe
        return _REAL_PYTHON

    # 候选2：项目虚拟环境（使用修复后的 PROJECT_ROOT）
    candidates = [
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
    ]

    # 候选3：系统 Python 路径
    candidates.extend([
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python312" / "python.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python311" / "python.exe",
        Path("C:/Program Files/Python312/python.exe"),
        Path("C:/Program Files/Python311/python.exe"),
        Path("C:/Python312/python.exe"),
        Path("C:/Python311/python.exe"),
    ])

    for candidate in candidates:
        if candidate.exists():
            _REAL_PYTHON = str(candidate)
            logger.info(f"🔍 沙盒找到 Python: {_REAL_PYTHON}")
            return _REAL_PYTHON

    # 候选4：PATH 上的 python
    import shutil
    for name in ["python", "python3", "py"]:
        found = shutil.which(name)
        if found:
            # 验证不是 PyInstaller exe 自身
            if "7tan-editor" not in found.lower():
                _REAL_PYTHON = found
                logger.info(f"🔍 沙盒找到 Python (PATH): {_REAL_PYTHON}")
                return _REAL_PYTHON

    # 最后回退：在 frozen 环境下找不到独立 Python 时直接报错
    # 不要 fallback 到 sys.executable，因为它指向 exe 自身，会导致启动新 GUI 窗口
    if is_frozen:
        raise FileNotFoundError(
            "找不到独立 Python 解释器。请安装 Python 3.11+ 到系统，"
            "或将 Python 添加到 PATH 环境变量。"
        )
    _REAL_PYTHON = sys.executable
    return _REAL_PYTHON


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

        # 找到真正的 Python 解释器
        python_exe = _find_real_python()
        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen:
            cmd = [python_exe, str(script_path)]
        else:
            cmd = [python_exe, "-I", str(script_path)]

        logger.debug(f"🔧 沙盒执行: {' '.join(cmd)}")

        # 设置 SANDBOX_MODE 环境变量，防止子进程意外启动 GUI
        env = os.environ.copy()
        env["SANDBOX_MODE"] = "1"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(SANDBOX_ROOT),
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )

        # 防御性处理：在某些环境下 stdout/stderr 可能为 None
        stdout = (result.stdout or "")[:MAX_OUTPUT_SIZE]
        stderr = (result.stderr or "")[:MAX_OUTPUT_SIZE]

        if result.returncode == 0:
            return f"✅ 执行成功\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        else:
            return f"❌ 执行失败 (退出码 {result.returncode})\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"

    except subprocess.TimeoutExpired:
        return "⏰ 沙盒执行超时"
    except FileNotFoundError:
        return "❌ 找不到 Python 解释器，请检查系统是否安装了 Python 3"
    except Exception as e:
        return f"❌ 沙盒执行异常: {e}"
    finally:
        # 清理
        if script_path.exists():
            script_path.unlink()


@register_tool(
    name="self_rebuild",
    description="重新构建打包整个项目。修改源码后调用此工具，自动运行 build.bat 生成新的 exe。构建完成后需要调用 self_restart 重启。",
    parameters={
        "type": "object",
        "properties": {
            "build_script": {
                "type": "string",
                "description": "构建脚本路径，默认为项目根目录下的 build.bat",
                "default": "build.bat"
            },
            "timeout": {
                "type": "integer",
                "description": "构建超时秒数（构建通常需要 5-15 分钟）",
                "default": 900
            },
        },
        "required": []
    },
    category="self_modify",
)
def self_rebuild(build_script: str = "build.bat", timeout: int = 900) -> str:
    """重新构建打包项目"""
    build_path = PROJECT_ROOT / build_script
    if not build_path.exists():
        # 也尝试在运行目录查找
        build_path = Path(build_script)
        if not build_path.exists():
            return f"❌ 找不到构建脚本: {build_script}\n  已搜索:\n    - {PROJECT_ROOT / build_script}\n    - {Path(build_script).absolute()}"

    logger.warning(f"🔨 开始重新构建: {build_path}")

    try:
        result = subprocess.run(
            [str(build_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )

        stdout = result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout
        stderr = result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr

        if result.returncode == 0:
            return f"✅ 构建成功！\n--- 构建输出（最后5000字符）---\n{stdout}\n--- stderr ---\n{stderr}"
        else:
            return f"❌ 构建失败 (退出码 {result.returncode})\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"

    except subprocess.TimeoutExpired:
        return f"⏰ 构建超时（超过 {timeout} 秒）"
    except Exception as e:
        return f"❌ 构建异常: {e}"


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
)
def self_update_prompt(prompt_type: str, new_template: str, reason: str) -> str:
    """更新系统提示词"""
    from ..agent.prompts import update_prompt
    try:
        update_prompt(prompt_type, new_template, reason)
        return f"✅ 提示词已更新: {prompt_type}\n原因: {reason}"
    except Exception as e:
        return f"❌ 更新失败: {e}"


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
    """验证完整性"""
    from ..security.integrity import verify_integrity
    return verify_integrity()


@register_tool(
    name="self_restart",
    description="自动重启应用程序。AI 可以调用此工具来重启自己。重启后约3秒新窗口会自动打开。",
    parameters={
        "type": "object",
        "properties": {
            "delay_seconds": {"type": "integer", "description": "重启前等待秒数，默认2秒", "default": 2},
        },
        "required": []
    },
    category="self_modify",
)
def self_restart(delay_seconds: int = 2) -> str:
    """重启应用程序"""
    logger.warning("🔄 正在重启...")
    import subprocess
    import os

    exe_path = sys.executable
    if not os.path.exists(exe_path):
        return f"❌ 找不到可执行文件: {exe_path}"

    # 启动新进程
    subprocess.Popen([exe_path], creationflags=0x00000008 if os.name == 'nt' else 0)

    # 退出当前进程
    os._exit(0)
    return "🔄 正在重启..."
