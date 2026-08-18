"""
插件管理器 — 安装/卸载/加载插件工具
"""
import json
import os
import sys
import shutil
import importlib.util
import importlib
from pathlib import Path
from typing import Optional
from loguru import logger

# 项目根目录
ROOT = Path(__file__).parent.parent.parent
PLUGIN_DIR = ROOT / "data" / "plugins"
MANIFEST_FILE = PLUGIN_DIR / "manifest.json"
INSTALLED_FILE = PLUGIN_DIR / "installed.json"


class PluginManager:
    """插件生命周期管理器"""

    def __init__(self):
        self._loaded_modules = {}  # plugin_id -> module

    # === 清单管理 ===

    def get_manifest(self) -> list:
        """获取可用插件清单"""
        if not MANIFEST_FILE.exists():
            return self._default_manifest()
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            return self._default_manifest()

    def get_installed(self) -> list:
        """获取已安装的插件 ID 列表"""
        if not INSTALLED_FILE.exists():
            return []
        try:
            data = json.loads(INSTALLED_FILE.read_text(encoding="utf-8"))
            return data.get("plugins", [])
        except Exception:
            return []

    def _save_installed(self, plugin_ids: list):
        """保存已安装列表"""
        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        INSTALLED_FILE.write_text(
            json.dumps({"plugins": plugin_ids}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # === 安装/卸载 ===

    def install(self, plugin_id: str) -> dict:
        """安装插件"""
        manifest = self.get_manifest()
        plugin_info = None
        for p in manifest:
            if p.get("id") == plugin_id:
                plugin_info = p
                break

        if not plugin_info:
            return {"ok": False, "error": f"未找到插件: {plugin_id}"}

        # 远程插件走下载流程
        if plugin_info.get("type") == "remote":
            return self._install_remote(plugin_id, plugin_info)

        # 内置插件直装
        pkg_dir = PLUGIN_DIR / plugin_id
        if not pkg_dir.exists():
            return {"ok": False, "error": f"插件目录不存在: {pkg_dir}"}

        try:
            self._load_plugin(plugin_id, str(pkg_dir))
        except Exception as e:
            logger.error(f"加载插件 {plugin_id} 失败: {e}")
            return {"ok": False, "error": str(e)}

        # 记录安装
        installed = self.get_installed()
        if plugin_id not in installed:
            installed.append(plugin_id)
            self._save_installed(installed)

        tool_count = len(plugin_info.get("tools", []))
        return {"ok": True, "message": f"✅ 插件 {plugin_info.get('name', plugin_id)} 安装成功 ({tool_count} 个工具)", "tools": tool_count}

    def _install_remote(self, plugin_id: str, info: dict) -> dict:
        """从远程源安装插件"""
        import requests
        import shutil

        url = info.get("source_url")
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            code = resp.text
        except Exception as e:
            return {"ok": False, "error": f"下载失败: {e}"}

        # 创建插件目录
        pkg_dir = PLUGIN_DIR / plugin_id
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # 保存工具代码
        tool_file = pkg_dir / "tools.py"
        tool_file.write_text(code, encoding="utf-8")

        # 保存元数据
        meta_file = pkg_dir / "plugin.json"
        meta_file.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

        # 加载
        try:
            self._load_plugin(plugin_id, str(pkg_dir))
        except Exception as e:
            shutil.rmtree(pkg_dir, ignore_errors=True)
            return {"ok": False, "error": str(e)}

        installed = self.get_installed()
        if plugin_id not in installed:
            installed.append(plugin_id)
            self._save_installed(installed)

        tool_count = len(info.get("tools", []))
        return {"ok": True, "message": f"✅ 插件 {info.get('name', plugin_id)} 安装成功 ({tool_count} 个工具)", "tools": tool_count}

    def uninstall(self, plugin_id: str) -> dict:
        """卸载插件（保留目录）"""
        installed = self.get_installed()
        if plugin_id not in installed:
            return {"ok": False, "error": f"插件 {plugin_id} 未安装"}

        # 卸载模块
        self._unload_plugin(plugin_id)

        # 更新安装列表
        installed.remove(plugin_id)
        self._save_installed(installed)

        # 不删除目录（保留用户修改），但标记为未安装
        return {"ok": True, "message": f"🗑️ 插件已卸载（工具代码保留在 data/plugins/{plugin_id}/）"}

    # === pyc 缓存清理 ===

    @staticmethod
    def _clear_pycache(pkg_dir: str):
        """删除插件目录的 __pycache__，防止 .pyc 缓存导致旧代码被加载"""
        pycache = Path(pkg_dir) / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache, ignore_errors=True)
            logger.debug(f"🧹 清理 pyc 缓存: {pycache}")

    @staticmethod
    def _clear_all_pycache():
        """清理所有插件目录的 __pycache__"""
        if not PLUGIN_DIR.exists():
            return
        count = 0
        for pkg_dir in PLUGIN_DIR.iterdir():
            if not pkg_dir.is_dir():
                continue
            pycache = pkg_dir / "__pycache__"
            if pycache.exists():
                shutil.rmtree(pycache, ignore_errors=True)
                count += 1
        if count > 0:
            logger.info(f"🧹 启动时清理了 {count} 个插件的 pyc 缓存")

    # === 模块加载/卸载 ===

    def _load_plugin(self, plugin_id: str, pkg_dir: str):
        """动态加载插件工具模块（哈希白名单校验已解除，默认直接加载）

        🔒 2026-08-14 变更：哈希白名单校验默认解除（用户决定）。
           - 解除模式（默认）：先尝试 SHA-256 白名单校验，任何失败不再拒绝
             加载，回退到直接加载（_load_direct），彻底消除
             "改 tools.py 后忘记重生成 hashes.json → 插件拒载" 问题。
           - 恢复严格模式：设置环境变量 7TAN_PLUGIN_HASH_VERIFY=1，
             此时校验失败将拒绝加载（原行为）。
        🔴 三重保险确保不加载 .pyc 缓存：
        1. 删除 __pycache__ 目录
        2. importlib.invalidate_caches() 清除内部缓存
        3. 从 sys.modules 中移除旧模块再重新加载
        """
        tools_path = Path(pkg_dir) / "tools.py"
        if not tools_path.exists():
            logger.warning(f"插件 {plugin_id} 无 tools.py")
            return

        # 🔴 保险1: 删除 pyc 缓存文件
        self._clear_pycache(pkg_dir)
        # 🔴 保险2: 清除 importlib 内部缓存
        importlib.invalidate_caches()

        # 如果之前已加载，先卸载旧版本（清理 TOOL_REGISTRY）
        if plugin_id in self._loaded_modules:
            self._unload_plugin(plugin_id)

        strict = os.environ.get("7TAN_PLUGIN_HASH_VERIFY", "0") == "1"
        if strict:
            # 严格模式：哈希白名单校验，失败则拒绝加载
            from ..security.plugin_guard import verify_and_load
            module = verify_and_load(plugin_id, pkg_dir, str(PLUGIN_DIR / "hashes.json"))
            self._loaded_modules[plugin_id] = module
            logger.info(f"📦 插件已加载: {plugin_id}（严格校验通过）")
            return

        # 解除模式（默认）：先尝试校验，失败则直接加载，不拦截
        try:
            from ..security.plugin_guard import verify_and_load
            module = verify_and_load(plugin_id, pkg_dir, str(PLUGIN_DIR / "hashes.json"))
            self._loaded_modules[plugin_id] = module
            logger.info(f"📦 插件已加载: {plugin_id}（哈希校验通过）")
        except Exception as e:
            logger.warning(
                f"插件 {plugin_id} 哈希白名单校验未通过（{str(e)[:60]}），"
                f"已解除拦截，直接加载")
            module = self._load_direct(plugin_id, pkg_dir)
            self._loaded_modules[plugin_id] = module
            logger.info(f"📦 插件已加载: {plugin_id}（绕过白名单）")

    def _load_direct(self, plugin_id: str, pkg_dir: str):
        """直接加载插件模块（不经过哈希白名单校验）"""
        tools_path = Path(pkg_dir) / "tools.py"
        module_name = f"plugin_{plugin_id}"
        if module_name in sys.modules:
            del sys.modules[module_name]
        self._clear_pycache(pkg_dir)
        importlib.invalidate_caches()
        spec = importlib.util.spec_from_file_location(module_name, tools_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _unload_plugin(self, plugin_id: str):
        """从注册表中移除插件的所有工具"""
        from ..tools.registry import TOOL_REGISTRY
        # 找到这个插件注册的工具并移除
        to_remove = []
        for name, tool in TOOL_REGISTRY.items():
            func = tool.function
            if func is None:
                continue
            mod_name = getattr(func, '__module__', '')
            if mod_name.startswith(f'plugin_{plugin_id}'):
                to_remove.append(name)

        for name in to_remove:
            del TOOL_REGISTRY[name]
            logger.info(f"🔧 卸载工具: {name}")

        # 从 sys.modules 移除
        module_name = f"plugin_{plugin_id}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        if plugin_id in self._loaded_modules:
            del self._loaded_modules[plugin_id]

    # === 生命周期 ===

    def load_all_installed(self):
        """启动时加载所有已安装的插件（单个失败不影响整体）"""
        # 🔴 启动时全局清理 pyc 缓存
        self._clear_all_pycache()
        importlib.invalidate_caches()

        installed = self.get_installed()
        manifest = self.get_manifest()
        manifest_map = {p.get("id"): p for p in manifest}

        self._load_errors = {}  # 记录加载失败的插件及原因
        for pid in installed:
            info = manifest_map.get(pid, {"type": "builtin"})
            pkg_dir = PLUGIN_DIR / pid
            if pkg_dir.exists():
                try:
                    self._load_plugin(pid, str(pkg_dir))
                except Exception as e:
                    self._load_errors[pid] = str(e)
                    logger.warning(f"加载插件 {pid} 失败: {e}")
            else:
                self._load_errors[pid] = "插件目录不存在"
                logger.warning(f"插件 {pid} 目录不存在: {pkg_dir}")

        if self._load_errors:
            logger.warning(
                f"{len(self._load_errors)}/{len(installed)} 个插件加载失败: "
                f"{', '.join(f'{k}({v[:30]})' for k, v in self._load_errors.items())}")

    def get_load_errors(self) -> dict:
        """获取插件加载错误信息"""
        return getattr(self, '_load_errors', {})

    def get_plugin_status(self, plugin_id: str) -> str:
        """获取插件状态: installed / available"""
        if plugin_id in self.get_installed():
            return "installed"
        return "available"

    # === 本地搜索 ===

    def _search_local(self, keyword: str = "") -> list:
        """搜索本地已安装和内置插件"""
        manifest = self.get_manifest()
        installed = self.get_installed()
        results = []
        kw = keyword.lower()
        for p in manifest:
            pid = p.get("id", "")
            if kw and kw not in pid.lower() and kw not in p.get("name", "").lower():
                continue
            entry = dict(p)
            entry["installed"] = pid in installed
            results.append(entry)
        return results

    # === 全网搜索 ===

    REMOTE_MANIFEST_URL = "https://raw.githubusercontent.com/7tan/7tan-plugins/main/manifest.json"

    def search_online(self, keyword: str = "") -> list:
        """搜索全网插件 — 通过 DuckDuckGo 搜索 GitHub/PyPI

        Args:
            keyword: 搜索关键词

        Returns:
            搜索结果列表
        """
        # 若配置了远程清单，先尝试下载
        try:
            import requests
            resp = requests.get(self.REMOTE_MANIFEST_URL, timeout=10)
            if resp.status_code == 200:
                remote_manifest = resp.json()
                if keyword:
                    kw_lower = keyword.lower()
                    return [
                        p for p in remote_manifest
                        if kw_lower in p.get("name", "").lower()
                        or kw_lower in p.get("description", "").lower()
                        or kw_lower in p.get("category", "").lower()
                    ]
                return remote_manifest
        except Exception:
            pass

        return []

    def get_plugin_info(self, plugin_id: str) -> Optional[dict]:
        """获取单个插件信息"""
        manifest = self.get_manifest()
        for p in manifest:
            if p.get("id") == plugin_id:
                return p
        return None

    # === 默认清单 ===

    def _default_manifest(self) -> list:
        """内置插件清单"""
        return [
            {
                "id": "tts_piper",
                "name": "TTS 语音合成 (Piper + Edge TTS)",
                "version": "1.2.0",
                "author": "7tanAI Team",
                "type": "builtin",
                "category": "AI / 语音",
                "description": "女声 Piper 本地推理 + 男声 Edge TTS 在线合成，双引擎自动回退。支持逐句流式播放。",
                "tools": ["tts_speak", "tts_status", "tts_set_gender", "tts_stop"],
                "icon": "🔊",
            },
            {
                "id": "browser_automation",
                "name": "浏览器自动化",
                "version": "1.0.0",
                "author": "7tanAI Team",
                "type": "builtin",
                "category": "工具",
                "description": "操控浏览器浏览网页、截图、点击、提取图片和下载链接。",
                "tools": ["browse_page", "screenshot", "click_element", "get_page_images", "find_download_links", "scroll_down"],
                "icon": "🌐",
            },
            {
                "id": "form_enhance",
                "name": "表单增强",
                "version": "1.0.0",
                "author": "7tanAI Team",
                "type": "builtin",
                "category": "工具",
                "description": "自动检测和填写表单字段。",
                "tools": ["detect_form_fields", "fill_all_fields"],
                "icon": "📝",
            },
            {
                "id": "price_monitor",
                "name": "价格监控",
                "version": "1.0.0",
                "author": "7tanAI Team",
                "type": "builtin",
                "category": "监控",
                "description": "监控 Steam/Epic/TapTap 等平台游戏价格变动和打折信息。通过搜索获取实时价格。",
                "tools": ["check_price", "price_alert"],
                "icon": "💰",
            },
            {
                "id": "ocr_reader",
                "name": "OCR 文字识别",
                "version": "1.0.0",
                "author": "7tanAI Team",
                "type": "builtin",
                "category": "AI / 识别",
                "description": "对截图进行 OCR 文字识别，提取页面中的游戏名称、版本号等信息。",
                "tools": ["ocr_screenshot"],
                "icon": "👁️",
            },
            {
                "id": "auto_screenshotter",
                "name": "自动截图",
                "version": "1.0.0",
                "author": "7tanAI Team",
                "type": "builtin",
                "category": "工具",
                "description": "对当前页面自动截取高质量截图，用于获取游戏详情页预览图。",
                "tools": ["auto_screenshot", "extract_logo"],
                "icon": "📸",
            },
        ]


def get_manager() -> PluginManager:
    """获取全局插件管理器单例"""
    global _manager_singleton
    if '_manager_singleton' not in globals():
        _manager_singleton = PluginManager()
    return _manager_singleton
