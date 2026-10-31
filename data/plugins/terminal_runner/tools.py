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
import time


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


def _scope_api():
    """取命令作用域模块；不可用时返回 None（调用方需显式提示，不能静默降级）。"""
    try:
        from src.utils import cmd_scope
        return cmd_scope
    except Exception:
        return None


def _resolve_or_error(cwd, tool: str = "run_command"):
    """解析 cwd 并按作用域校验，返回 (绝对路径, 拒绝原因)。"""
    api = _scope_api()
    if api is None:
        return Path(cwd or "."), None
    try:
        return api.resolve_cwd(cwd), None
    except api.ScopeViolation as e:
        return None, str(e)


def _audit(*args, **kwargs) -> dict:
    """写审计记录；模块不可用或写失败时返回带 _written=False 的记录，不吞掉。"""
    api = _scope_api()
    if api is None:
        return {"_written": False, "_write_error": "cmd_scope 模块不可用"}
    try:
        return api.audit(*args, **kwargs)
    except Exception as e:
        return {"_written": False, "_write_error": f"{type(e).__name__}: {e}"}


def _run_cmd(cmd: list, cwd: str = None, timeout: int = 120, raw: str = None,
             tool: str = "run_command", resolved_cwd=None) -> str:
    """通用命令执行器：cwd 过作用域校验 → 执行 → 全量审计落盘。

    两道围栏都在这里落地：
      ① cwd 越界（严格作用域下）直接拒绝，不执行、不降级；
      ② 无论成功/失败/超时/中止，都会写一条审计到 data/logs/cmd_audit.jsonl。
    """
    api = _scope_api()
    display = raw if raw is not None else " ".join(str(x) for x in cmd)

    if resolved_cwd is None:
        target, refuse = _resolve_or_error(cwd, tool)
        if refuse:
            _audit(tool, display, cwd, None, rc=None, duration_ms=0, error=refuse)
            return (f"🚫 已拒绝执行（工作目录越界）: {refuse}\n"
                    f"作用域外不得启动命令。若确实需要在别处执行，应让派工方把作用域的根目录指到该处。")
        resolved_cwd = target

    started = time.time()
    rc, so, se = None, "", ""
    note, err, aborted_flag = "", "", False

    try:
        from src.utils.abort_signal import run_with_abort, AbortedError
        try:
            rc, so, se = run_with_abort(cmd, cwd=str(resolved_cwd) if resolved_cwd else None,
                                        timeout=timeout)
        except AbortedError:
            aborted_flag = True
            note = "⏹ 已中止（用户终止任务），命令已强制结束"
        else:
            out = []
            if (so or "").strip():
                out.append(so.strip())
            if (se or "").strip():
                out.append(f"[stderr]\n{se.strip()}")
            if rc != 0:
                out.append(f"\n⚠️ 退出码: {rc}")
            note = "\n".join(out) if out else "(无输出)"
    except subprocess.TimeoutExpired:
        err = f"timeout {timeout}s"
        note = f"⏱ 命令超时 ({timeout}秒)"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        note = f"❌ 执行失败: {e}"
    finally:
        dur = round((time.time() - started) * 1000, 1)
        rec = _audit(tool, display, cwd, resolved_cwd, rc=rc, duration_ms=dur,
                     stdout=so or "", stderr=se or "", timeout=timeout,
                     aborted=aborted_flag, error=err)
        if not rec.get("_written"):
            note += f"\n⚠️ 审计写入失败（{rec.get('_write_error')}）——本条命令未留痕"

    if api is not None:
        sc = api.current()
        if sc is not None:
            esc = api.detect_escape(display, sc.root)
            if esc["suspicious"]:
                hits = (esc["outside_paths"] + esc["cd_up"])[:3]
                note += f"\n⚠️ 命令疑似触碰作用域外路径 {hits}（已记入审计）"

    return note


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
        # 被护栏拦下的命令同样留痕：事后能看出「谁想执行什么、为什么没执行」
        _audit("run_command", command, cwd, None, rc=None, duration_ms=0,
               error=f"guard_refused: {reason}", extra={"refused": True})
        return (f"🚫 已拒绝执行（命令护栏）: {reason}\n"
                f"请只传入真正的 shell 命令（如 dir / python script.py / git status），"
                f"不要把对话内容、文档、表格或说明文字当作命令执行。")
    if platform.system() == "Windows":
        cmd = ["cmd", "/c", command]
    else:
        cmd = ["bash", "-c", command]
    return _run_cmd(cmd, cwd=cwd, timeout=timeout, raw=command)


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


# ─────────────────────────────────────────────────────────────
# 🔍 命令审计检索：事后可查
# ─────────────────────────────────────────────────────────────
@register_tool(
    name="cmd_audit_query",
    description=(
        "检索命令审计流水（data/logs/cmd_audit.jsonl）。每条通过工具执行的 shell 命令都会落盘："
        "时间、作用域（interactive=人在场 / worker=无人值守）、cwd、命令原文、退出码、耗时、输出摘要、"
        "是否触碰作用域外路径。用于事后追查「谁在什么时候执行了什么、结果如何」。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "返回最近多少条，默认 20", "default": 20},
            "keyword": {"type": "string", "description": "按命令/输出/工具名关键词过滤", "default": ""},
            "scope": {"type": "string", "description": "按作用域过滤，如 worker / interactive / w-xxxx", "default": ""},
            "only_failed": {"type": "boolean", "description": "只看失败（退出码非 0 或有错误）", "default": False},
            "only_escape": {"type": "boolean", "description": "只看疑似触碰作用域外路径的命令", "default": False},
        },
        "required": [],
    },
    category="terminal",
)
def cmd_audit_query(limit: int = 20, keyword: str = "", scope: str = "",
                    only_failed: bool = False, only_escape: bool = False) -> str:
    """检索命令审计流水"""
    api = _scope_api()
    if api is None:
        return "❌ cmd_scope 模块不可用，无法读取审计流水"

    rows = api.query(limit=limit, keyword=keyword, scope=scope,
                     only_failed=only_failed, only_escape=only_escape)
    path = api.audit_path()
    if not rows:
        return f"📭 没有匹配的审计记录（文件：{path}）"

    out = [f"📜 命令审计流水（{path}）  命中 {len(rows)} 条，最近的在前："]
    for r in rows:
        flag = "✅" if r.get("rc") == 0 else ("⏱" if r.get("timeout") and r.get("rc") is None else "⚠️")
        if r.get("error"):
            flag = "❌"
        sc = r.get("scope") or "?"
        ms = r.get("duration_ms")
        dur = f"{ms}ms" if ms is not None else "?"
        cmdline = str(r.get("command") or "").replace("\n", " ⏎ ")
        if len(cmdline) > 130:
            cmdline = cmdline[:130] + "…"
        out.append(f"  {flag} {r.get('ts')}  [{sc}]  rc={r.get('rc')}  {dur}  {r.get('tool')}")
        out.append(f"      {cmdline}")
        if r.get("cwd"):
            out.append(f"      cwd: {r.get('cwd')}")
        if r.get("error"):
            out.append(f"      err: {str(r.get('error'))[:160]}")
        if r.get("escape"):
            hits = (r.get("outside") or [])[:3]
            out.append(f"      ⚠️ 作用域外线索: {hits}")
    return "\n".join(out)
