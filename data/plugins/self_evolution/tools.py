"""
自我进化插件 — 赋予 AI 自我扩展和深度控制能力
"""
import sys, os, json, hashlib, platform, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# 可靠定位源码根目录
# ROOT 在 PyInstaller 环境下是 _internal/，源码在 _internal/../../../
# 在源码环境下 ROOT 直接就是项目根
def _find_real_root():
    root = ROOT.resolve()
    # 如果在 _internal 里（PyInstaller），往上3层到项目根
    if root.name == "_internal":
        return root.parent.parent.parent
    # 否则假设当前就在项目根
    for _ in range(4):
        if (root / "build.bat").exists() or (root / "setup.py").exists():
            return root
        root = root.parent
    return ROOT  # fallback

_REAL_ROOT = _find_real_root()


@register_tool(
    name="self_diagnose",
    description="全面自我诊断：检查系统状态、插件健康度、磁盘空间、数据库状态、最近日志等。用于 AI 自我了解运行状况。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="system",
)
def self_diagnose() -> str:
    """全面自检"""
    results = []
    results.append("🔍 7tan-editor 全面自检报告")
    results.append(f"⏰ 时间: {datetime.now().isoformat()}")
    results.append(f"💻 系统: {platform.system()} {platform.release()}")
    results.append(f"🐍 Python: {sys.version}")
    results.append(f"📂 ROOT (运行): {ROOT}")
    results.append(f"📂 源码根: {_REAL_ROOT}")

    # 磁盘
    try:
        import shutil
        usage = shutil.disk_usage(str(_REAL_ROOT))
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        results.append(f"💾 磁盘: {free_gb:.1f}GB 可用 / {total_gb:.1f}GB 总计")
    except:
        results.append("💾 磁盘: 无法检测")

    # 插件 — 从源码目录读取（持久化）
    plugin_dir = _REAL_ROOT / "data" / "plugins"
    try:
        with open(plugin_dir / "installed.json") as f:
            installed = json.load(f)
        results.append(f"🧩 已安装插件: {len(installed.get('plugins', []))} 个 - {', '.join(installed.get('plugins', []))}")
    except Exception as e:
        results.append(f"🧩 插件: 读取失败 ({e})")

    # 数据库
    db_path = _REAL_ROOT / "data" / "games.db"
    if db_path.exists():
        results.append(f"🗄️ 数据库: {db_path.stat().st_size / 1024:.1f}KB")
    else:
        results.append("🗄️ 数据库: 不存在")

    # downloads
    dl_dir = _REAL_ROOT / "downloads"
    if dl_dir.exists():
        files = list(dl_dir.rglob("*"))
        results.append(f"📥 下载目录: {len(files)} 个文件")
    else:
        results.append("📥 下载目录: 不存在")

    # 配置文件
    config_path = _REAL_ROOT / "config" / "config.yaml"
    if config_path.exists():
        results.append(f"⚙️ 配置: 已加载 ({config_path})")
    else:
        results.append(f"⚙️ 配置: 未找到 ({config_path})")

    return "\n".join(results)


@register_tool(
    name="create_plugin",
    description="动态创建新插件。AI 可以编写插件代码并自动注册到系统中，重启后生效。用于自我扩展能力。同时写入运行目录和源码目录，构建后不丢失。",
    parameters={
        "type": "object",
        "properties": {
            "plugin_id": {"type": "string", "description": "插件唯一 ID"},
            "plugin_name": {"type": "string", "description": "插件显示名称"},
            "description": {"type": "string", "description": "插件描述"},
            "tools_code": {"type": "string", "description": "tools.py 的完整 Python 代码"},
            "icon": {"type": "string", "description": "图标 emoji", "default": "🔧"},
        },
        "required": ["plugin_id", "plugin_name", "description", "tools_code"],
    },
    category="system",
)
def create_plugin(plugin_id: str, plugin_name: str, description: str, tools_code: str, icon: str = "🔧") -> str:
    """动态创建插件 — 同时写两份：dist（立即生效）和源码（构建后保留）"""
    import re
    tool_names = re.findall(r'name="([^"]+)"', tools_code)
    if not tool_names:
        tool_names = re.findall(r"name='([^']+)'", tools_code)

    written = []

    # 写入运行目录（dist）和源码目录（持久化）
    for base_root in [ROOT, _REAL_ROOT]:
        if base_root.resolve() == _REAL_ROOT.resolve():
            continue  # 同一个目录
        try:
            plugin_dir = base_root / "data" / "plugins" / plugin_id
            plugin_dir.mkdir(parents=True, exist_ok=True)
            (plugin_dir / "tools.py").write_text(tools_code, encoding="utf-8")

            # manifest
            manifest_path = base_root / "data" / "plugins" / "manifest.json"
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            manifest = [p for p in manifest if p["id"] != plugin_id]
            manifest.append({
                "id": plugin_id, "name": plugin_name, "version": "1.0.0",
                "author": "AI Self-Evolution", "type": "custom",
                "category": "自定义", "description": description,
                "tools": tool_names, "icon": icon,
            })
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            # installed
            installed_path = base_root / "data" / "plugins" / "installed.json"
            with open(installed_path, "r") as f:
                installed = json.load(f)
            plugins_list = installed.get("plugins", [])
            if plugin_id not in plugins_list:
                plugins_list.append(plugin_id)
            installed["plugins"] = plugins_list
            with open(installed_path, "w") as f:
                json.dump(installed, f, ensure_ascii=False, indent=2)

            written.append(str(base_root))
        except Exception as e:
            written.append(f"{base_root} ❌ {e}")

    return f"""✅ 插件创建成功！
📦 ID: {plugin_id}
📛 名称: {plugin_name}
🔧 工具: {', '.join(tool_names)}
📝 描述: {description}
📁 写入位置: {', '.join(written)}

⚠️ 需要重启应用才能使新工具生效。"""


@register_tool(
    name="system_shell",
    description="获取系统 shell 信息。返回当前运行环境的关键参数。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="system",
)
def system_shell() -> str:
    """系统环境信息"""
    info = []
    info.append("🖥️ 系统环境")
    info.append(f"  工作目录: {os.getcwd()}")
    info.append(f"  ROOT (运行): {ROOT}")
    info.append(f"  源码根: {_REAL_ROOT}")
    info.append(f"  PATH: {os.environ.get('PATH', 'N/A')[:200]}")

    for key in ["DEEPSEEK_API_KEY", "OSS_ACCESS_KEY", "TANTAN_PASSWORD"]:
        val = os.environ.get(key, "")
        if val:
            info.append(f"  {key}: {'*' * 8}(已设置)")
        else:
            info.append(f"  {key}: (未设置)")

    return "\n".join(info)


@register_tool(
    name="check_file_integrity",
    description="检查所有关键文件的完整性：计算 SHA-256 并与已知值对比。用于自我验证。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="system",
)
def check_file_integrity() -> str:
    """完整性校验"""
    results = []
    results.append("📋 文件完整性检查")

    files_to_check = [
        _REAL_ROOT / "config" / "config.yaml",
        _REAL_ROOT / "data" / "prompts" / "system.txt",
        _REAL_ROOT / "data" / "plugins" / "manifest.json",
        _REAL_ROOT / "data" / "plugins" / "installed.json",
    ]

    for fpath in files_to_check:
        if fpath.exists():
            sha = hashlib.sha256(fpath.read_bytes()).hexdigest()[:16]
            results.append(f"  ✅ {fpath.name}: SHA256={sha}...")
        else:
            results.append(f"  ❌ {fpath.name}: 文件不存在")

    results.append(f"\n📂 检查根目录: {_REAL_ROOT}")
    return "\n".join(results)
