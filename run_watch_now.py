# -*- coding: utf-8 -*-
"""临时引导：直接加载 desktop_watch 插件并执行监控（无需重启应用）"""
import sys, os, types, importlib.util

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# 桩掉 register_tool 装饰器，避免拉起完整注册表链
fake_pkg = types.ModuleType('src'); fake_pkg.__path__ = []
fake_tools = types.ModuleType('src.tools'); fake_tools.__path__ = []
fake_reg = types.ModuleType('src.tools.registry')
def _stub_register(**kw):
    def deco(f): return f
    return deco
fake_reg.register_tool = _stub_register
sys.modules['src'] = fake_pkg
sys.modules['src.tools'] = fake_tools
sys.modules['src.tools.registry'] = fake_reg

spec = importlib.util.spec_from_file_location(
    'desktop_watch_plugin',
    os.path.join(ROOT, 'data', 'plugins', 'desktop_watch', 'tools.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print(mod.desktop_watch(seconds=300, interval=5, threshold=0.05,
                        keywords='更新失败', use_vlm=False))
