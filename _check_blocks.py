"""
检查 ARCHITECTURE.md 中的代码块完整性（调试工具）
用法: python _check_blocks.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
arch_file = ROOT / "ARCHITECTURE.md"

if not arch_file.exists():
    print(f"❌ 文件不存在: {arch_file}")
    sys.exit(1)

with open(arch_file, "r", encoding="utf-8") as f:
    lines = f.readlines()
