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


# ===== 自修改审计日志 =====
def _audit_log(tool_name: str, params: dict, result: str):
    """记录自修改操作审计（谁/何时/改了什么），写入 logs/audit/"""
    try:
        root = Path(__file__).resolve().parent.parent.parent
        if not (root / "build.bat").exists():
            root = Path(sys.executable).parent
        audit_dir = root / "logs" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        safe_params = {k: (str(v)[:300] if v is not None else v) for k, v in params.items()}
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool": tool_name,
            "params": safe_params,
            "result": str(result)[:500],
        }
        with open(audit_dir / f"audit_{time.strftime('%Y%m%d')}.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"📝 自修改审计: {tool_name}")
    except Exception as e:
        logger.debug(f"审计日志写入失败: {e}")

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
        _audit_log("self_modify_config", {"key_path": key_path, "new_value": new_value[:200], "reason": reason}, "ok")
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


# ============================================================
# 沙盒文件变更快照 — 让代码修改实时面板能看到 sandbox_execute 的改动
# ============================================================

_SNAPSHOT_DIRS = ("src", "config", "data/prompts", "data/plugins")
_SNAPSHOT_SKIP_DIRS = {"__pycache__", ".venv", "node_modules", "dist", "build"}
_SNAPSHOT_EXTS = {".py", ".txt", ".yaml", ".yml", ".json", ".md", ".html", ".css", ".js", ".bat", ".sh"}
_SNAPSHOT_MAX_FILE = 300_000  # 超过 300KB 不存内容，只记录变更事实


def _snapshot_project_files() -> dict:
    """对项目关键目录做快照: {path_str: (mtime_ns, size, content_or_None)}"""
    root = _get_project_root()
    snap = {}
    for sub in _SNAPSHOT_DIRS:
        base = root / sub
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in _SNAPSHOT_EXTS:
                continue
            if any(part in _SNAPSHOT_SKIP_DIRS for part in p.parts):
                continue
            try:
                st = p.stat()
                content = None
                if st.st_size <= _SNAPSHOT_MAX_FILE:
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        content = None
                snap[str(p)] = (st.st_mtime_ns, st.st_size, content)
            except Exception:
                continue
    return snap


def _publish_sandbox_changes(before: dict):
    """执行后快照对比，把变更发布到代码修改实时面板（best-effort，绝不抛异常）"""
    try:
        from ..utils.code_change_bus import publish_file_change
        after = _snapshot_project_files()
        published = 0
        # 新建 / 修改
        for path, (mt, size, content) in after.items():
            old = before.get(path)
            if old is None:
                publish_file_change("create", path, new_text=content,
                                    summary="沙盒新建文件")
                published += 1
            elif old[0] != mt or old[1] != size:
                publish_file_change("write", path, old_text=old[2], new_text=content,
                                    summary="沙盒修改")
                published += 1
            if published >= 20:  # 防刷屏：单次最多 20 条
                break
        # 删除
        deleted = [p for p in before if p not in after]
        for path in deleted[:10]:
            publish_file_change("delete", path, old_text=before[path][2],
                                summary="沙盒删除")
            published += 1
        if published:
            logger.info(f"📡 沙盒变更已同步到代码面板: {published} 个文件")
    except Exception as e:
        logger.warning(f"沙盒变更快照对比失败（不影响执行结果）: {e}")


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
    # 自修改审计：记录执行内容摘要（与其它 self_modify 工具一致）
    _audit_log("sandbox_execute", {"code_hash": hashlib.sha256(code.encode()).hexdigest()[:12], "code_head": code[:200], "timeout": timeout}, "started")
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
    script_path = SANDBOX_ROOT / f"test_{code_hash}_{int(time.time())}.py"

    # 写入脚本
    script_path.write_text(code, encoding="utf-8")

    # ── 执行前快照（让代码修改实时面板能看到沙盒内发生的文件变更）──
    _before_snap = _snapshot_project_files()

    try:
        # 找到真正的 Python 解释器
        python_exe = _find_real_python()
        is_frozen = getattr(sys, 'frozen', False)

        # -I 隔离模式：无论是否打包都启用，防止沙盒代码污染宿主环境
        cmd = [python_exe, "-I", "-X", "utf8", str(script_path)]

        logger.debug(f"🔧 沙盒执行: {' '.join(cmd)}")

        # 设置 SANDBOX_MODE 环境变量，防止子进程意外启动 GUI
        env = os.environ.copy()
        env["SANDBOX_MODE"] = "1"
        # Windows 下子进程 stdout 默认按 GBK 编码，print emoji 会 UnicodeEncodeError；
        # 注意：-I(=-E -s) 会忽略所有 PYTHON* 环境变量，所以真正生效的是命令行 -X utf8
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

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

        # ── 执行后快照对比：沙盒内的文件变更发布到代码修改实时面板 ──
        _publish_sandbox_changes(_before_snap)

        if result.returncode == 0:
            # 成功：清理脚本文件
            try:
                if script_path.exists():
                    script_path.unlink()
            except Exception:
                pass
            return f"✅ 执行成功\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        else:
            # 失败：保留脚本文件以便调试，并记录到日志
            logger.error(f"❌ 沙盒执行失败 (退出码 {result.returncode})")
            logger.error(f"   脚本: {script_path}")
            logger.error(f"   命令: {' '.join(cmd)}")
            if stdout:
                logger.error(f"   stdout: {stdout[:500]}")
            if stderr:
                logger.error(f"   stderr: {stderr[:500]}")
            return (
                f"❌ 执行失败 (退出码 {result.returncode})\n"
                f"--- 脚本 ---\n{script_path}\n"
                f"--- stdout ---\n{stdout}\n"
                f"--- stderr ---\n{stderr}"
            )

    except subprocess.TimeoutExpired:
        logger.error(f"⏰ 沙盒执行超时 ({timeout}s): {script_path}")
        # 超时时进程可能已改过文件，也要对比
        _publish_sandbox_changes(_before_snap)
        return f"⏰ 沙盒执行超时 ({timeout}s)\n--- 脚本 ---\n{script_path}"
    except FileNotFoundError:
        logger.error("❌ 找不到 Python 解释器")
        return "❌ 找不到 Python 解释器，请检查系统是否安装了 Python 3\n--- 脚本 ---\n" + str(script_path)
    except Exception as e:
        logger.error(f"❌ 沙盒执行异常: {e}")
        return f"❌ 沙盒执行异常: {e}\n--- 脚本 ---\n{script_path}"


@register_tool(
    name="self_rebuild",
    description="重新构建打包整个项目。修改源码后调用此工具，自动运行 rebuild.bat 生成新的 exe。构建完成后需要调用 self_restart 重启。",
    parameters={
        "type": "object",
        "properties": {
            "build_script": {
                "type": "string",
                "description": "构建脚本路径，默认为项目根目录下的 rebuild.bat",
                "default": "rebuild.bat"
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
def self_rebuild(build_script: str = "rebuild.bat", timeout: int = 900) -> str:
    """重新构建打包项目"""
    build_path = PROJECT_ROOT / build_script
    if not build_path.exists():
        # 也尝试在运行目录查找
        build_path = Path(build_script)
        if not build_path.exists():
            return f"❌ 找不到构建脚本: {build_script}\n  已搜索:\n    - {PROJECT_ROOT / build_script}\n    - {Path(build_script).absolute()}"

    logger.warning(f"🔨 开始重新构建: {build_path}")
    _audit_log("self_rebuild", {"build_script": build_script, "timeout": timeout}, "started")

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
    _audit_log("self_update_prompt", {"prompt_type": prompt_type, "reason": reason, "template_head": new_template[:200]}, "started")
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
    category="monitor",
)
def self_restart(delay_seconds: int = 2) -> str:
    """重启应用程序 — AI 工具调用入口，委托给 daemon.py:graceful_restart()"""
    from ..scheduler.daemon import graceful_restart
    logger.warning("🔄 正在重启（AI 工具触发）...")
    _audit_log("self_restart", {"delay_seconds": delay_seconds}, "started")
    graceful_restart(delay_seconds=delay_seconds, close_browser_flag=False)
    return "🔄 正在重启..."
