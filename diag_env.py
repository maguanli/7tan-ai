import sys, subprocess
print("Python 路径:", sys.executable)
print("Python 版本:", sys.version.split()[0])
print("-" * 50)
# 检查关键 GUI 依赖
for pkg in ["PyQt6", "PyQt6-WebEngine", "PyQt5", "PySide6"]:
    try:
        __import__(pkg.replace("-", "_").split("_")[0])
        print(f"[有] {pkg}")
    except ImportError:
        print(f"[无] {pkg}")
