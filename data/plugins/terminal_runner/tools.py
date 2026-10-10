"""
终端运行器插件 — 增强的命令执行、构建、测试、依赖安装
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import subprocess
import os
import platform


# ─────────────────────────────────────────────────────────────
# 🛡️ 命令护栏：防止 AI 把对话/文档/表格/说明文字当作 shell 命令执行
# （历史事故：AI 曾把 markdown 表格粘贴内容直接交给 cmd /c 执行）
# ─────────────────────────────────────────────────────────────
_MD_SIGNS = ("**", "`", "###", "---", "✅", "❌", "⚠️", "🚫", "🔧", "🎯", "📋", "📦", "①", "②", "③", "→", "▶", "●", "•", "【", "】")
_SAFE_CMD_PREFIXES = (
    "echo", "dir", "cd", "cls", "type", "copy", "del", "mkdir", "rmdir", "move", "ren",
    "python", "pip", "git", "npm", "node", "npx", "yarn", "pnpm", "go", "cargo", "rustc",
    "mvn", "gradle", "make", "cmake", "powershell", "pwsh", "cmd", "start", "set", "for",
    "if", "reg", "schtasks", "ping", "ipconfig", "net", "curl", "wget", "tasklist",
    "taskkill", "find", "findstr", "where", "tree", "attrib", "xcopy", "robocopy", "pause",
    "exit", "color", "title", "systeminfo", "ver", "whoami", "hostname", "date", "time",
    "chkdsk", "sfc", "dism", "bcdedit", "notepad", "explorer", "calc", "py", "java",
    "javac", "kotlin", "swift", "docker", "kubectl", "helm", "ssh", "scp", "rsync",
)


def _guard_command(command: str) -> tuple:
    """命令护栏：返回 (是否允许, 拒绝原因)。拦截非命令文本被当作 shell 命令执行。"""
    c = (command or "").strip()
    if not c:
        return False, "命令为空"
    if len(c) > 2000:
        return False, f"命令过长（{len(c)}字符，上限2000），疑似粘贴了整段内容"
    # 1) markdown / 富文本 / 文档特征 → 拦截
    for sign in _MD_SIGNS:
        if sign in c:
            return False, f"参数含富文本特征「{sign}」，疑似对话/文档/表格内容，不是 shell 命令"
    # 2) 特殊符号开头 → 粘贴片段特征
    if c[0] in "|&<>(){};!*?[]~%":
        return False, f"命令以特殊字符「{c[0]}」开头，疑似文本片段"
    # 3) 含竖线管道且夹杂中文 → 疑似表格行（合法纯 ASCII 管道命令不受影响）
    if "|" in c:
        cjk = sum(1 for ch in c if '\u4e00' <= ch <= '\u9fff')
        if cjk > 0:
            return False, "参数含竖线且夹杂中文，疑似表格/文档内容"
    # 4) 中文占比过高且首词不是已知命令 → 疑似自然语言
    first_word = c.split()[0].lower() if c.split() else ""
    if first_word not in _SAFE_CMD_PREFIXES:
        cjk = sum(1 for ch in c if '\u4e00' <= ch <= '\u9fff')
        if len(c) > 0 and cjk / len(c) >= 0.3:
            return False, "参数以中文为主，疑似自然语言/说明文字，不是 shell 命令"
    return True, ""


def _run_cmd(cmd: list, cwd: str = None, timeout: int = 120) -> str:
    """通用命令执行器（支持用户中止：中止时立即杀掉子进程树）"""
    try:
        from src.utils.abort_signal import run_with_abort, AbortedError
        try:
            rc, so, se = run_with_abort(cmd, cwd=cwd or None, timeout=timeout)
        except AbortedError:
            return "⏹ 已中止（用户终止任务），命令已强制结束"
        out = []
        if (so or "").strip():
            out.append(so.strip())
        if (se or "").strip():
            out.append(f"[stderr]\n{se.strip()}")
        if rc != 0:
            out.append(f"\n⚠️ 退出码: {rc}")
        return "\n".join(out) if out else "(无输出)"
    except subprocess.TimeoutExpired:
        return f"⏱ 命令超时 ({timeout}秒)"
    except Exception as e:
        return f"❌ 执行失败: {e}"


@register_tool(
    name="run_command",
    description="在项目目录中执行任意 shell 命令，返回标准输出和错误输出。适合运行构建脚本、脚本文件等。⚠️ 只允许真正的 shell 命令（如 dir / python script.py / git status）；严禁把对话内容、文档、表格或说明文字当作命令执行——此类参数会被命令护栏自动拒绝。",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的命令"},
            "cwd": {"type": "string", "description": "工作目录路径", "default": "."},
            "timeout": {"type": "integer", "description": "超时秒数，默认120", "default": 120},
        },
        "required": ["command"]
    },
    category="terminal"
)
def run_command(command: str, cwd: str = ".", timeout: int = 120) -> str:
    """执行 shell 命令（带命令护栏，拒绝非命令文本）"""
    ok, reason = _guard_command(command)
    if not ok:
        return (f"🚫 已拒绝执行（命令护栏）: {reason}\n"
                f"请只传入真正的 shell 命令（如 dir / python script.py / git status），"
                f"不要把对话内容、文档、表格或说明文字当作命令执行。")
    if platform.system() == "Windows":
        cmd = ["cmd", "/c", command]
    else:
        cmd = ["bash", "-c", command]
    return _run_cmd(cmd, cwd=cwd, timeout=timeout)


@register_tool(
    name="run_build",
    description="自动检测项目类型并执行构建命令。支持 Python(setup/pyproject)、Node(npm build)、Go、Rust、Maven、Gradle。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="terminal"
)
def run_build(path: str = ".") -> str:
    """自动检测并构建项目"""
    if not os.path.isdir(path):
        return f"目录不存在: {path}"

    # 检测项目类型
    files = os.listdir(path)
    if "pyproject.toml" in files or "setup.py" in files or "setup.cfg" in files:
        return _run_cmd(["pip", "install", "-e", "."], cwd=path, timeout=300)
    elif "package.json" in files:
        return _run_cmd(["npm", "run", "build"], cwd=path, timeout=300)
    elif "go.mod" in files:
        return _run_cmd(["go", "build", "./..."], cwd=path, timeout=300)
    elif "Cargo.toml" in files:
        return _run_cmd(["cargo", "build"], cwd=path, timeout=600)
    elif "pom.xml" in files:
        return _run_cmd(["mvn", "package", "-DskipTests"], cwd=path, timeout=600)
    elif "build.gradle" in files or "build.gradle.kts" in files:
        cmd = ["gradlew.bat", "build"] if platform.system() == "Windows" else ["./gradlew", "build"]
        return _run_cmd(cmd, cwd=path, timeout=600)
    elif "Makefile" in files:
        return _run_cmd(["make"], cwd=path, timeout=300)
    else:
        return "未检测到已知的构建系统。可尝试手动使用 run_command 执行构建命令。"


@register_tool(
    name="install_deps",
    description="自动检测项目类型并安装依赖。支持 Python(pip/poetry)、Node(npm/yarn/pnpm)、Go、Rust。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="terminal"
)
def install_deps(path: str = ".") -> str:
    """安装项目依赖"""
    if not os.path.isdir(path):
        return f"目录不存在: {path}"

    files = os.listdir(path)
    if "poetry.lock" in files or ("pyproject.toml" in files and
                                   self._has_poetry(path)):
        return _run_cmd(["poetry", "install"], cwd=path, timeout=300)
    elif "pyproject.toml" in files:
        return _run_cmd(["pip", "install", "-e", ".[dev]"], cwd=path, timeout=300)
    elif "requirements.txt" in files:
        return _run_cmd(["pip", "install", "-r", "requirements.txt"], cwd=path, timeout=300)
    elif "setup.py" in files:
        return _run_cmd(["pip", "install", "-e", "."], cwd=path, timeout=300)
    elif "yarn.lock" in files:
        return _run_cmd(["yarn", "install"], cwd=path, timeout=300)
    elif "pnpm-lock.yaml" in files:
        return _run_cmd(["pnpm", "install"], cwd=path, timeout=300)
    elif "package-lock.json" in files:
        return _run_cmd(["npm", "ci"], cwd=path, timeout=300)
    elif "package.json" in files:
        return _run_cmd(["npm", "install"], cwd=path, timeout=300)
    elif "go.mod" in files:
        return _run_cmd(["go", "mod", "download"], cwd=path, timeout=300)
    elif "Cargo.toml" in files:
        return _run_cmd(["cargo", "fetch"], cwd=path, timeout=300)
    else:
        return "未检测到依赖管理文件。请使用 run_command 手动安装依赖。"


def _has_poetry(path):
    try:
        with open(os.path.join(path, "pyproject.toml"), "r") as f:
            return "[tool.poetry]" in f.read()
    except Exception:
        return False


@register_tool(
    name="check_env",
    description="检查开发环境：Python/Node/Go/Rust 版本、Git 状态、可用磁盘空间。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="terminal"
)
def check_env() -> str:
    """检查开发环境"""
    checks = []
    for cmd, name in [(["python", "--version"], "Python"),
                       (["node", "--version"], "Node.js"),
                       (["npm", "--version"], "npm"),
                       (["git", "--version"], "Git"),
                       (["go", "version"], "Go"),
                       (["cargo", "--version"], "Rust/Cargo")]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                              creationflags=subprocess.CREATE_NO_WINDOW)
            ver = r.stdout.strip() or r.stderr.strip()
            checks.append(f"✅ {name}: {ver}")
        except Exception:
            pass
    return "\n".join(checks) if checks else "未检测到开发工具"
