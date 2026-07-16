@echo off
cd /d D:\7tan\7tanAI
C:\Program Files\Python312\python.exe -c "
import sys
sys.path.insert(0, '.')
print('=== sys.path ===')
for p in sys.path[:5]:
    print(f'  {p}')
print()
print('=== testing import ===')
try:
    from src.tools.registry import register_tool
    print('OK: register_tool imported successfully')
    print(f'register_tool = {register_tool}')
except Exception as e:
    print(f'FAIL: {e}')
print()
print('=== testing direct from data/plugins ===')
import importlib.util
spec = importlib.util.spec_from_file_location('test_qq', r'data\plugins\qq_bridge\tools.py')
print(f'spec = {spec}')
if spec:
    mod = importlib.util.module_from_spec(spec)
    sys.modules['test_qq'] = mod
    try:
        spec.loader.exec_module(mod)
        print('OK: qq_bridge tools.py loaded successfully')
    except Exception as e:
        print(f'FAIL: {e}')
"
