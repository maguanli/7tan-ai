"""
配置管理器 — .env 管理、密钥泄露检测、配置验证
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os
import re


@register_tool(
    name="manage_env",
    description="管理项目的 .env 文件：列出所有变量（隐藏值）、添加/更新变量、检查缺失的必要变量。",
    parameters={
        "type": "object",
        "properties": {
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
            "action": {"type": "string", "description": "操作: list/add/set/check", "default": "list"},
            "key": {"type": "string", "description": "变量名（add/set 时必填）", "default": ""},
            "value": {"type": "string", "description": "变量值（add/set 时必填）", "default": ""},
        },
        "required": []
    },
    category="config"
)
def manage_env(project_root: str = ".", action: str = "list",
               key: str = "", value: str = "") -> str:
    """管理 .env"""
    env_path = os.path.join(project_root, ".env")

    if action == "list":
        if not os.path.isfile(env_path):
            return f"⚠️ .env 文件不存在: {env_path}"

        results = [f"📋 .env 变量:"]
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        masked = v[:4] + "***" if len(v) > 4 else "***"
                        results.append(f"  {k}={masked}")
        except Exception as e:
            return f"读取失败: {e}"
        return "\n".join(results) if len(results) > 1 else "📋 .env 为空"

    elif action in ("add", "set"):
        if not key or not value:
            return "⚠️ add/set 操作需要 key 和 value 参数"

        lines = []
        exists = False
        if os.path.isfile(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                if action == "set":
                    new_lines.append(f"{key}={value}\n")
                    exists = True
                else:
                    return f"⚠️ 变量 '{key}' 已存在。使用 action=set 来更新。"
            else:
                new_lines.append(line)

        if not exists:
            if lines and not lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"{key}={value}\n")
            action_word = "添加" if not exists else "更新"
        else:
            action_word = "更新"

        with open(env_path, "w") as f:
            f.writelines(new_lines)
        return f"✅ 已{action_word}: {key}=***"

    elif action == "check":
        common_vars = ["SECRET_KEY", "API_KEY", "DATABASE_URL", "REDIS_URL",
                       "DEBUG", "ENVIRONMENT", "PORT", "HOST"]
        if not os.path.isfile(env_path):
            return "⚠️ .env 不存在。建议创建并配置以下变量:\n  " + "\n  ".join(common_vars)

        with open(env_path, "r") as f:
            content = f.read()

        missing = []
        for var in common_vars:
            if re.search(rf'^{var}\s*=', content, re.MULTILINE):
                continue
            if var == "DEBUG":
                missing.append(f"  {var}=False (建议添加)")
            elif var == "SECRET_KEY":
                missing.append(f"  {var}=<随机字符串> (强烈建议)")
            else:
                missing.append(f"  {var}=<值>")

        if missing:
            return f"⚠️ 缺少常见变量:\n" + "\n".join(missing)
        return "✅ 所有常见变量已配置"

    return f"未知操作: {action}。可用: list/add/set/check"


@register_tool(
    name="scan_secrets",
    description="扫描项目代码中可能泄露的密钥、密码、Token 等敏感信息。检查 .env、config.py、settings.py 等。",
    parameters={
        "type": "object",
        "properties": {
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
            "severity": {"type": "string", "description": "最低严重度: high/medium/low", "default": "medium"},
        },
        "required": []
    },
    category="config"
)
def scan_secrets(project_root: str = ".", severity: str = "medium") -> str:
    """扫描密钥泄露"""
    patterns = {
        "high": [
            # API Keys
            (r'(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*["\'][^"\']{8,}["\']', "API Key 硬编码"),
            (r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^"\']{3,}["\']', "密码硬编码"),
            (r'(?:token|access_token)\s*[:=]\s*["\'][^"\']{8,}["\']', "Token 硬编码"),
            (r'(?:sk-[a-zA-Z0-9]{20,})', "OpenAI API Key"),
            (r'(?:ghp_[a-zA-Z0-9]{36})', "GitHub Personal Access Token"),
            (r'(?:AKIA[0-9A-Z]{16})', "AWS Access Key"),
        ],
        "medium": [
            (r'(?:private[_-]?key|private_key)\s*[:=]\s*["\']{3,}', "私钥"),
            (r'(?:database[_-]?url|db[_-]?url)\s*[:=]\s*["\']', "数据库连接字符串"),
            (r'(?:smtp|email)_(?:password|pass)\s*[:=]\s*["\']', "邮箱密码"),
        ],
        "low": [
            (r'(?:debug)\s*[:=]\s*True', "DEBUG=True"),
            (r'os\.environ\.get\(["\']([^"\']+)["\']\)', "环境变量引用"),
        ],
    }

    results = []
    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv",
                 "dist", "build", ".tox", ".eggs", "recordings", "logs"}
    scan_extensions = {".py", ".js", ".ts", ".yml", ".yaml", ".json", ".env",
                       ".ini", ".cfg", ".toml", ".sh", ".bat"}

    for level in ["high", "medium", "low"]:
        if severity == "high" and level != "high":
            continue
        if severity == "medium" and level == "low":
            continue

        for pattern, desc in patterns[level]:
            compiled = re.compile(pattern, re.IGNORECASE)
            for root, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in scan_extensions and fname != ".env" and fname != "Dockerfile":
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, 1):
                                if compiled.search(line):
                                    rel = os.path.relpath(fpath, project_root)
                                    prefix = "🔴" if level == "high" else "🟡" if level == "medium" else "🔵"
                                    results.append(
                                        f"  {prefix} [{level}] {rel}:{i} — {desc}: {line.strip()[:150]}"
                                    )
                    except Exception:
                        pass

    if not results:
        return "✅ 未发现密钥泄露"
    return f"⚠️ 发现 {len(results)} 处潜在密钥泄露:\n\n" + "\n".join(results[:30])


@register_tool(
    name="generate_env_template",
    description="扫描项目代码中的 os.environ/os.getenv 调用，生成 .env.example 模板文件。",
    parameters={
        "type": "object",
        "properties": {
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="config"
)
def generate_env_template(project_root: str = ".") -> str:
    """生成 .env.example"""
    env_vars = set()
    # 扫描环境变量引用
    patterns = [
        r'os\.environ(?:\[|\.get\()["\']([A-Z_][A-Z0-9_]*)["\']',
        r'os\.getenv\(["\']([A-Z_][A-Z0-9_]*)["\']',
        r'config\(["\']([A-Z_][A-Z0-9_]*)["\']',
        r'env(?:\[|\.get\()["\']([A-Z_][A-Z0-9_]*)["\']',
    ]

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".env", ".sh")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        for pat in patterns:
                            for m in re.finditer(pat, line):
                                env_vars.add(m.group(1))
            except Exception:
                pass

    if not env_vars:
        return "未发现环境变量引用"

    known_defaults = {
        "DEBUG": "False", "PORT": "8000", "HOST": "0.0.0.0",
        "LOG_LEVEL": "INFO", "ENVIRONMENT": "production",
    }

    lines = ["# 环境变量配置模板", f"# 复制为 .env 并填入实际值\n"]
    for var in sorted(env_vars):
        default = known_defaults.get(var, f"<{var}>")
        lines.append(f"{var}={default}")

    template = "\n".join(lines) + "\n"
    filepath = os.path.join(project_root, ".env.example")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)
    return f"✅ .env.example 已生成 ({len(env_vars)} 个变量)"
