"""
插件系统 — 动态工具加载/卸载
"""
from .manager import PluginManager, get_manager

__all__ = ["PluginManager", "get_manager"]
