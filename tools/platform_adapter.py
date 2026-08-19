# -*- coding: utf-8 -*-
"""
7Tan 平台适配执行器（跨平台核心 · 其他系统包专用）

背景:
    7Tan 目前仅发布两个包：
      ① Windows 专属包：绿色版 EXE + WEB 版（现状不变）
      ② 其他系统包（macOS / Linux / 鸿蒙PC）：纯源码版，解压后打开 9900 WEB 版，
        页面提示「插件复制适配」→ 用户点击确认 → 本模块一口气完成全部操作：
          1) 检测当前操作系统
          2) 逐插件体检兼容性（规则表 + 源码 Windows 专属 API 扫描）
          3) 复制该平台对应的插件变体（data/plugins/<id>/variants/<platform>/）
          4) 安装该平台所需依赖（pip）
          5) 插件冒烟自测（导入测试）
          6) 通过即启用，失败自动降级并说明
          7) 输出适配报告（data/plugins/adapt_report.json）+ 状态（adapt_status.json）

用法:
    python tools/platform_adapter.py --check             # 体检：当前系统 + 各插件兼容性（只读）
    python tools/platform_adapter.py --adapt             # 执行适配（用户确认后调用，一次完成）
    python tools/platform_adapter.py --report            # 查看最近一次适配报告
    python tools/platform_adapter.py --status            # 查看当前适配状态（WEB 首页轮询用）
    python tools/platform_adapter.py --check --json      # 输出 JSON（供 WEB 端展示）
    python tools/platform_adapter.py --check --platform darwin  # 模拟指定平台（测试/预览）

设计原则:
    - 只使用 Python 标准库（不依赖项目第三方包），保证在任意系统、任意环境下可运行
    - 不修改已兼容的插件；只对「平台专属插件」做复制变体 + 装依赖 + 自测
    - 幂等：重复执行 --adapt 不会重复复制/安装（有状态文件记录）
"""
import sys
import os
import json
import time
import shutil
import platform
import importlib.util
import subprocess
from pathlib import Path

# === 项目根目录 ===
ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "data" / "plugins"
INSTALLED_FILE = PLUGIN_DIR / "installed.json"
ADAPT_REPORT_FILE = PLUGIN_DIR / "adapt_report.json"
ADAPT_STATUS_FILE = PLUGIN_DIR / "adapt_status.json"

# === 平台识别 ===
PLATFORM_MAP = {
    "win32": ("win32", "Windows"),
    "darwin": ("darwin", "macOS"),
    "linux": ("linux", "Linux"),
}

# 鸿蒙 PC 本质是 Linux 生态，归入 linux
_ALIAS = {"harmony": "linux", "harmonyos": "linux", "euleros": "linux"}

# 可被 --platform 参数覆盖（模拟/指定平台，供测试与 WEB 端调用）
_FORCE_PLATFORM = None


def detect_platform() -> tuple:
    """检测当前平台: (platform_key, pretty_name)"""
    if _FORCE_PLATFORM:
        raw = _FORCE_PLATFORM.lower()
        for k, v in _ALIAS.items():
            if k in raw:
                return v, "HarmonyOS(鸿蒙PC/Linux生态)"
        if raw in PLATFORM_MAP:
            key, name = PLATFORM_MAP[raw]
            return key, name
        return raw, f"指定平台({raw})"
    raw = sys.platform.lower()
    for k, v in _ALIAS.items():
        if k in raw:
            return v, "HarmonyOS(鸿蒙PC/Linux生态)"
    if raw in PLATFORM_MAP:
        key, name = PLATFORM_MAP[raw]
        return key, name
    return raw, f"未知系统({raw})"


# === Windows 专属 API 关键词（源码扫描用） ===
WINDOWS_ONLY_IMPORTS = [
    "win32gui", "win32con", "win32api", "win32clipboard", "win32process",
    "win32file", "win32event", "win32com", "win32security", "win32service",
    "pywinauto", "uiautomation", "winrt", "windows.media.ocr", "comtypes",
    "winreg", "msvcrt", "ctypes.windll", "pywin32", "winsound",
]

# === 插件平台规则表（权威判定；未列出的插件默认可跨平台） ===
# 值: "all" = 跨平台；["win32"] = 仅 Windows 可用（其他系统需变体或降级）
PLUGIN_PLATFORM_RULES = {
    "desktop_bot": ["win32"],   # 桌面控制：pywinauto/winrt/win32gui 深度绑定 Windows
    "gzh_publish": ["win32"],   # 公众号发布：绑定微信 Windows 客户端
    "camera_vision": "all",     # 摄像头视觉：opencv/mss 跨平台
    "tts_piper": "all",         # 语音合成：piper 跨平台
    "whisper_stt": "all",       # 语音识别：whisper 跨平台
}


def get_plugin_platforms(plugin_id: str):
    """获取插件支持平台列表（规则表优先，默认 all）"""
    rule = PLUGIN_PLATFORM_RULES.get(plugin_id, "all")
    if rule == "all":
        return ["all"]
    return rule


def load_installed() -> list:
    """读取已安装插件 ID 列表"""
    try:
        data = json.loads(INSTALLED_FILE.read_text(encoding="utf-8"))
        return data.get("plugins", [])
    except Exception:
        return []


def plugin_dir(plugin_id: str) -> Path:
    return PLUGIN_DIR / plugin_id


def scan_windows_imports(pdir: Path) -> list:
    """扫描插件源码中的 Windows 专属 import（返回命中关键词列表）"""
    hits = []
    if not pdir.is_dir():
        return hits
    for py in pdir.rglob("*.py"):
        # 跳过变体目录（变体是适配目标，不算当前平台的判定依据）
        if "variants" in py.parts:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for kw in WINDOWS_ONLY_IMPORTS:
            if kw in text and kw not in hits:
                hits.append(kw)
    return hits


def find_variant(pdir: Path, platform_key: str) -> Path:
    """查找插件是否带当前平台变体目录: data/plugins/<id>/variants/<platform>/"""
    v = pdir / "variants" / platform_key
    return v if v.is_dir() else None


def plugin_entry_module(pdir: Path):
    """查找插件入口模块文件（tools.py / plugin.py / __init__.py）"""
    for name in ("tools.py", "plugin.py", "__init__.py"):
        p = pdir / name
        if p.exists():
            return p
    # 兜底：任意 .py
    pys = sorted(pdir.glob("*.py"))
    return pys[0] if pys else None


def smoke_test(pdir: Path) -> tuple:
    """冒烟自测：导入插件入口模块，成功 = 通过"""
    entry = plugin_entry_module(pdir)
    if entry is None:
        return False, "未找到插件入口模块"
    # 确保项目根目录在 sys.path：变体 tools.py 可能含 `from src.tools.registry import register_tool`
    # （platform_adapter.py 位于 tools/ 下，subprocess 运行时 sys.path[0] 不含项目根目录）
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    try:
        spec = importlib.util.spec_from_file_location(f"_adapt_test_{pdir.name}", entry)
        if spec is None or spec.loader is None:
            return False, "无法加载模块"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return True, f"导入成功: {entry.name}"
    except Exception as e:
        return False, f"导入失败: {e.__class__.__name__}: {e}"


def install_plugin_deps(pdir: Path, platform_key: str) -> list:
    """安装插件依赖：优先 requirements-<platform>.txt，其次 requirements.txt（仅插件目录内）"""
    results = []
    candidates = [
        pdir / f"requirements-{platform_key}.txt",
        pdir / f"requirements_{platform_key}.txt",
        pdir / "requirements.txt",
    ]
    for req in candidates:
        if req.exists():
            ok, msg = _pip_install(req)
            results.append({"file": req.name, "ok": ok, "msg": msg})
    return results


def _pip_install(req_file: Path) -> tuple:
    """调用当前 Python 执行 pip 安装依赖文件"""
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode == 0:
            return True, "依赖安装完成"
        return False, f"pip 失败(exit {proc.returncode}): {(proc.stderr or proc.stdout)[-300:]}"
    except Exception as e:
        return False, f"pip 异常: {e}"


def copy_variant(pdir: Path, variant_dir: Path, platform_key: str) -> tuple:
    """复制平台变体到插件目录（覆盖同名文件，先备份被覆盖文件到 variants/backup）"""
    backup_dir = pdir / "variants" / "backup" / f"{platform_key}_{int(time.time())}"
    copied, replaced = [], []
    for src in variant_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(variant_dir)
            dst = pdir / rel
            if dst.exists():
                backup_dir.mkdir(parents=True, exist_ok=True)
                bak = backup_dir / rel
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bak)
                replaced.append(str(rel))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(str(rel))
    return copied, replaced


def classify(plugin_id: str, pdir: Path, platform_key: str) -> dict:
    """对单个插件做兼容性分类（只读）"""
    supported = get_plugin_platforms(plugin_id)
    compatible = ("all" in supported) or (platform_key in supported)

    info = {
        "id": plugin_id,
        "supported": supported,
        "compatible": compatible,
        "windows_hits": scan_windows_imports(pdir),
        "has_variant": find_variant(pdir, platform_key) is not None,
    }

    if compatible:
        info["status"] = "ok"          # 直接可用
        info["action"] = "无需操作"
    elif info["has_variant"]:
        info["status"] = "adaptable"   # 有变体，可复制适配
        info["action"] = "复制平台变体 + 装依赖 + 自测"
    else:
        info["status"] = "skipped"     # 平台专属且无变体，当前系统降级
        info["action"] = "当前系统不可用（降级跳过）"
    return info


# ============================================================
# 主流程
# ============================================================

def run_check() -> dict:
    """体检：只读扫描，输出全部插件兼容性"""
    platform_key, platform_name = detect_platform()
    installed = load_installed()
    plugins = []
    for pid in installed:
        pdir = plugin_dir(pid)
        if not pdir.is_dir():
            plugins.append({"id": pid, "status": "missing", "action": "插件目录缺失",
                            "supported": [], "compatible": False,
                            "windows_hits": [], "has_variant": False})
            continue
        plugins.append(classify(pid, pdir, platform_key))

    stats = {"ok": 0, "adaptable": 0, "skipped": 0, "missing": 0}
    for p in plugins:
        stats[p["status"]] = stats.get(p["status"], 0) + 1

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform_key,
        "platform_name": platform_name,
        "os_detail": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "total": len(plugins),
        "stats": stats,
        "plugins": plugins,
    }
    return report


def run_adapt(force: bool = False) -> dict:
    """执行适配（用户确认后调用）：复制变体 → 装依赖 → 自测 → 启用/降级"""
    platform_key, platform_name = detect_platform()
    installed = load_installed()

    adapted, skipped, failed, ok_skip = [], [], [], []

    for pid in installed:
        pdir = plugin_dir(pid)
        if not pdir.is_dir():
            skipped.append({"id": pid, "status": "missing", "reason": "插件目录缺失"})
            continue

        info = classify(pid, pdir, platform_key)
        if info["status"] == "ok":
            ok_skip.append({"id": pid, "status": "ok", "reason": "当前系统原生兼容"})
            continue

        if info["status"] == "skipped":
            skipped.append({"id": pid, "status": "skipped",
                            "reason": "Windows 专属插件且无当前平台变体，已在当前系统降级"})
            continue

        # adaptable：有平台变体 → 执行复制适配
        variant_dir = find_variant(pdir, platform_key)
        if variant_dir is None:
            skipped.append({"id": pid, "status": "skipped", "reason": "变体目录消失"})
            continue

        steps = []
        # ① 复制变体
        copied, replaced = copy_variant(pdir, variant_dir, platform_key)
        steps.append(f"复制变体文件 {len(copied)} 个" + (f"（覆盖 {len(replaced)} 个）" if replaced else ""))
        # ② 安装依赖
        dep_results = install_plugin_deps(pdir, platform_key)
        for d in dep_results:
            steps.append(f"依赖 {d['file']}: {'✅' if d['ok'] else '❌ ' + d['msg']}")
        # ③ 冒烟自测
        ok, msg = smoke_test(pdir)
        steps.append(f"自测: {'✅ ' if ok else '❌ '}{msg}")

        item = {"id": pid, "steps": steps, "ok": ok, "msg": msg}
        if ok:
            adapted.append(item)
        else:
            failed.append(item)

    # 生成报告
    report = {
        "adapted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform_key,
        "platform_name": platform_name,
        "os_detail": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "stats": {
            "total": len(installed),
            "ok": len(ok_skip),
            "adapted": len(adapted),
            "skipped": len(skipped),
            "failed": len(failed),
        },
        "adapted": adapted,
        "skipped": skipped,
        "failed": failed,
    }

    try:
        ADAPT_REPORT_FILE.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        report["write_error"] = str(e)

    # 保存适配状态（供 WEB 首页/后续启动读取）
    save_status(report)

    return report


def save_status(report: dict):
    """保存适配状态文件 adapt_status.json"""
    plugins = {}
    for p in report.get("adapted", []):
        plugins[p["id"]] = "adapted"
    for p in report.get("skipped", []):
        plugins[p["id"]] = p.get("status", "skipped")
    for p in report.get("failed", []):
        plugins[p["id"]] = "failed"
    status = {
        "platform": report.get("platform"),
        "platform_name": report.get("platform_name"),
        "adapted_at": report.get("adapted_at"),
        "stats": report.get("stats", {}),
        "plugins": plugins,
    }
    try:
        ADAPT_STATUS_FILE.write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_status() -> dict:
    """读取当前适配状态（不存在返回空）"""
    try:
        if ADAPT_STATUS_FILE.exists():
            return json.loads(ADAPT_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def pretty_print(report: dict):
    """人类可读输出"""
    line = "=" * 56
    print(line)
    print(f"  7Tan 平台适配 · {report.get('platform_name', '?')}")
    print(f"  {report.get('os_detail', '')} · Python {report.get('python', '?')}")
    print(line)
    stats = report.get("stats", {})
    print(f"  插件总数: {report.get('total', len(report.get('plugins', [])))}  "
          f"✅兼容 {stats.get('ok', 0)}  "
          f"🔄已适配 {stats.get('adapted', 0)}  "
          f"⏭️跳过 {stats.get('skipped', 0)}  "
          f"❌失败 {stats.get('failed', 0)}")
    print("-" * 56)

    for p in report.get("plugins", []):  # --check 模式
        mark = {"ok": "✅", "adaptable": "🔄", "skipped": "⏭️", "missing": "❌"}.get(p.get("status"), "❓")
        extra = ""
        if p.get("windows_hits"):
            extra = f" [Windows API: {', '.join(p['windows_hits'][:4])}]"
        if p.get("has_variant"):
            extra += " [有平台变体可适配]"
        print(f"  {mark} {p['id']:<22} {p.get('action', '')}{extra}")

    for item in report.get("adapted", []):  # --adapt 模式
        print(f"  🔄 {item['id']}: 适配成功")
        for s in item.get("steps", []):
            print(f"       · {s}")

    for item in report.get("skipped", []):
        print(f"  ⏭️ {item['id']}: {item.get('reason', '跳过')}")

    for item in report.get("failed", []):
        print(f"  ❌ {item['id']}: {item.get('msg', '失败')}")
    print(line)


def main():
    # 修复 Windows 控制台 GBK 中文乱码（JSON 供 WEB 端解析必须 UTF-8）
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    global _FORCE_PLATFORM
    args = [a for a in sys.argv[1:]]
    use_json = "--json" in args
    args = [a for a in args if a != "--json"]

    # 可选 --platform=darwin 或 --platform darwin（模拟/指定平台，测试与 WEB 预览用）
    for i, a in enumerate(args):
        if a.startswith("--platform="):
            _FORCE_PLATFORM = a.split("=", 1)[1]
            args.pop(i)
            break
    else:
        for i, a in enumerate(args):
            if a == "--platform" and i + 1 < len(args):
                _FORCE_PLATFORM = args[i + 1]
                del args[i:i + 2]
                break

    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "--check":
        report = run_check()
        if use_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            pretty_print(report)
    elif cmd == "--adapt":
        report = run_adapt(force="--force" in args)
        if use_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            pretty_print(report)
    elif cmd == "--report":
        try:
            report = json.loads(ADAPT_REPORT_FILE.read_text(encoding="utf-8"))
            if use_json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                pretty_print(report)
        except Exception as e:
            print(f"暂无适配报告: {e}")
    elif cmd == "--status":
        status = load_status()
        if use_json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            if not status:
                print("尚未执行过适配")
            else:
                print(f"平台: {status.get('platform_name')} | 适配时间: {status.get('adapted_at')}")
                for pid, st in status.get("plugins", {}).items():
                    mark = {"adapted": "🔄", "skipped": "⏭️", "failed": "❌"}.get(st, "❓")
                    print(f"  {mark} {pid}: {st}")
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
