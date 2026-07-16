"""Test loading the qq_bridge plugin's tools.py"""
import sys
import os
import importlib.util

plugin_dir = os.path.join("D:\\7tan\\7tanAI", "data", "plugins", "qq_bridge")
tools_path = os.path.join(plugin_dir, "tools.py")

print(f"Tools path: {tools_path}")
print(f"File exists: {os.path.exists(tools_path)}")

# Read the file first
with open(tools_path, "r", encoding="utf-8") as f:
    content = f.read()

# Check if register_tool is defined before the decorator usage
# Find the line numbers
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def register_tool' in line:
        print(f"  Line {i+1}: def register_tool")
    if '@register_tool' in line:
        print(f"  Line {i+1}: @register_tool (decorator usage)")
    if 'TOOL_REGISTRY = _get_tool_registry()' in line:
        print(f"  Line {i+1}: TOOL_REGISTRY = _get_tool_registry()")

# Try importing it
sys.path.insert(0, plugin_dir)

try:
    spec = importlib.util.spec_from_file_location("plugin_qq_bridge_test", tools_path)
    if spec is None or spec.loader is None:
        print("ERROR: spec is None")
    else:
        module = importlib.util.module_from_spec(spec)
        sys.modules["plugin_qq_bridge_test"] = module
        spec.loader.exec_module(module)
        print("SUCCESS: Module loaded!")
        print(f"  Has register_tool: {hasattr(module, 'register_tool')}")
        print(f"  Has qq_connect: {hasattr(module, 'qq_connect')}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
