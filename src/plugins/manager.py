"""
插件管理器 — 安装/卸载/加载插件工具
"""
import json
import os
import sys
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

        installed = self.get_installed()
        if plugin_id in installed:
            return {"ok": False, "error": f"插件 {plugin_id} 已安装"}

        # 处理内置插件
        if plugin_info.get("type") == "builtin":
            return self._install_builtin(plugin_id, plugin_info)

        # 处理远程插件
        if plugin_info.get("source_url"):
            return self._install_remote(plugin_id, plugin_info)

        return {"ok": False, "error": "插件无安装源"}

    def _install_builtin(self, plugin_id: str, info: dict) -> dict:
        """安装内置插件 — 从 data/plugins/{id}/ 加载"""
        pkg_dir = PLUGIN_DIR / plugin_id
        if not pkg_dir.exists():
            return {"ok": False, "error": f"内置插件目录不存在: {pkg_dir}"}

        # 加载工具模块
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

        tool_count = len(info.get("tools", []))
        return {"ok": True, "message": f"✅ 插件 {info.get('name', plugin_id)} 安装成功 ({tool_count} 个工具)", "tools": tool_count}

    def _install_remote(self, plugin_id: str, info: dict) -> dict:
        """从远程源安装插件"""
        import requests
        import tempfile
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
        """卸载插件"""
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

    # === 模块加载/卸载 ===

    def _load_plugin(self, plugin_id: str, pkg_dir: str):
        """动态加载插件工具模块"""
        tools_path = Path(pkg_dir) / "tools.py"
        if not tools_path.exists():
            logger.warning(f"插件 {plugin_id} 无 tools.py")
            return

        # 如果之前已加载，先卸载旧版本
        if plugin_id in self._loaded_modules:
            self._unload_plugin(plugin_id)

        # 添加插件目录到 sys.path
        if pkg_dir not in sys.path:
            sys.path.insert(0, pkg_dir)

        module_name = f"plugin_{plugin_id}"
        spec = importlib.util.spec_from_file_location(module_name, str(tools_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {tools_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self._loaded_modules[plugin_id] = module
        logger.info(f"📦 插件已加载: {plugin_id}")

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

        if plugin_id in self._loaded_modules:
            del self._loaded_modules[plugin_id]

    # === 生命周期 ===

    def load_all_installed(self):
        """启动时加载所有已安装的插件"""
        installed = self.get_installed()
        manifest = self.get_manifest()
        manifest_map = {p.get("id"): p for p in manifest}

        for pid in installed:
            info = manifest_map.get(pid, {"type": "builtin"})
            pkg_dir = PLUGIN_DIR / pid
            if pkg_dir.exists():
                try:
                    self._load_plugin(pid, str(pkg_dir))
                except Exception as e:
                    logger.warning(f"加载插件 {pid} 失败: {e}")

    def get_plugin_status(self, plugin_id: str) -> str:
        """获取插件状态: installed / available"""
        if plugin_id in self.get_installed():
            return "installed"
        return "available"

    # === 默认清单 ===

    @staticmethod
    def _default_manifest() -> list:
        """内置插件清单"""
        return [
            {
                "id": "web_search",
                "name": "联网搜索",
                "version": "1.0.0",
                "author": "7tan",
                "type": "builtin",
                "category": "搜索",
                "description": "让 AI 能够搜索互联网获取最新资讯、游戏攻略、补丁信息",
                "tools": ["web_search", "fetch_news"],
                "icon": "🔍",
            },
            {
                "id": "deep_analysis",
                "name": "深度分析",
                "version": "1.0.0",
                "author": "7tan",
                "type": "builtin",
                "category": "分析",
                "description": "对游戏进行深度分析：评价、优缺点、用户反馈汇总、竞品对比",
                "tools": ["analyze_game", "compare_games", "summarize_reviews"],
                "icon": "📊",
            },
            {
                "id": "auto_images",
                "name": "自动配图",
                "version": "1.0.0",
                "author": "7tan",
                "type": "builtin",
                "category": "媒体",
                "description": "发布时自动从页面截取高清截图、提取 LOGO 并压缩优化",
                "tools": ["auto_screenshot", "extract_logo"],
                "icon": "🖼️",
            },
            {
                "id": "video_download",
                "name": "视频下载",
                "version": "1.0.0",
                "author": "7tan",
                "type": "remote",
                "category": "媒体",
                "description": "下载 YouTube/B站/抖音 游戏宣传视频，自动提取封面",
                "tools": ["download_video", "extract_thumbnail"],
                "source_url": "",
                "icon": "🎬",
            },
            {
                "id": "smart_translate",
                "name": "智能翻译",
                "version": "1.0.0",
                "author": "7tan",
                "type": "builtin",
                "category": "语言",
                "description": "自动翻译英文游戏介绍、Steam商店页面描述为中文",
                "tools": ["translate_text", "translate_page"],
                "icon": "🌐",
            },
            {
                "id": "price_monitor",
                "name": "价格监控",
                "version": "1.0.0",
                "author": "7tan",
                "type": "builtin",
                "category": "监控",
                "description": "监控 Steam/Epic/TapTap 等平台游戏价格变动和打折信息",
                "tools": ["check_price", "price_alert"],
                "icon": "💰",
            },
        ]


# 全局单例
_manager: Optional[PluginManager] = None


def get_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager
