"""检查 qq_bridge 插件导入问题"""
import sys
import importlib.util
from pathlib import Path

# 模拟插件加载
QRIDGE_PATH = Path(r"D:\7tan\7tanAI\data\plugins\qq_bridge\tools.py")
print(f"tools.py path: {QRIDGE_PATH}")
print(f"tools.py exists: {QRIDGE_PATH.exists()}")

# 计算 ROOT
ROOT = QRIDGE_PATH.parent.parent.parent.parent
print(f"ROOT (expected): {ROOT}")
print(f"ROOT exists: {ROOT.exists()}")

# 模拟 sys.path 修改
sys.path.insert(0, str(ROOT))

# 检查 src 是否可导入
src_in_path = [p for p in sys.path if Path(p, "src").is_dir()]
print(f"\nPaths containing src/ dir: {src_in_path}")

# 检查当前 sys.modules 中是否有 src
src_in_modules = [k for k in sys.modules.keys() if k.startswith('src')]
print(f"src in sys.modules: {src_in_modules}")

# 尝试导入
print("\n--- Attempting import ---")
try:
    from src.tools.registry import register_tool
    print("SUCCESS: register_tool imported!")
except Exception as e:
    print(f"FAILED: {e}")

    # 尝试更好的方法
    print("\n--- Alternative approach ---")
    try:
        # 直接通过 importlib 加载 registry 模块
        registry_path = ROOT / "src" / "tools" / "registry.py"
        print(f"registry.py path: {registry_path}")
        print(f"registry.py exists: {registry_path.exists()}")

        spec = importlib.util.spec_from_file_location(
            "src.tools.registry", str(registry_path)
        )
        if spec and spec.loader:
            registry_mod = importlib.util.module_from_spec(spec)
            sys.modules["src.tools.registry"] = registry_mod
            spec.loader.exec_module(registry_mod)
            register_tool = registry_mod.register_tool
            print(f"SUCCESS: register_tool imported via importlib: {register_tool}")
        else:
            print(f"spec is None or no loader")
    except Exception as e2:
        print(f"Alternative also failed: {e2}")
