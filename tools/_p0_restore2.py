# -*- coding: utf-8 -*-
"""检查并恢复 _internal / _python 中被误删的库文件（test_*.py / *.bak / *broken*）"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

VENV_SP = Path(r"D:\7tan\7tanAI\.venv\Lib\site-packages")
INTERNAL = Path(r"D:\7tan\7tanAI\dist\7tan-editor\_internal")
PY_SP = Path(r"D:\7tan\7tanAI\dist\_python\Lib\site-packages")

print("== pytest 在 .venv? ==")
pytest_dir = VENV_SP / "pytest"
print("  .venv pytest:", pytest_dir.exists())
if pytest_dir.exists():
    print("  ", list(pytest_dir.iterdir())[:5])
print()

def suspicious(p: Path) -> bool:
    n = p.name.lower()
    return "broken" in n or n.endswith((".bak", ".old")) or n.startswith("test_") or n.startswith("_fix") or n.startswith("_check") or n.startswith("_tmp")

# 统计 .venv 中可疑文件
venv_hits = [p for p in VENV_SP.rglob("*") if p.is_file() and suspicious(p)]
print(f".venv 中可疑文件数: {len(venv_hits)}")

# 对每个目标目录检查缺失并复制
restored = []
missing_src = []
for target_name, target_root in [("_internal", INTERNAL), ("_python", PY_SP)]:
    for p in venv_hits:
        rel = p.relative_to(VENV_SP)
        dst = target_root / rel
        if not dst.exists():
            # 目标里缺失（可能被误删）→ 从 .venv 复制
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(p.read_bytes())
                restored.append(f"{target_name}/{rel}")
            except Exception as e:
                missing_src.append(f"{target_name}/{rel}: {e}")

print(f"\n已从 .venv 恢复 {len(restored)} 个文件:")
for r in restored[:80]:
    print(f"  + {r}")
if len(restored) > 80:
    print(f"  ... 共 {len(restored)} 个")
print(f"\n恢复失败: {len(missing_src)}")
for m in missing_src[:10]:
    print(f"  ! {m}")

# 最终抽查
checks = [
    INTERNAL / "aiohttp" / "test_utils.py",
    INTERNAL / "Crypto" / "SelfTest" / "Cipher" / "test_AES.py",
    PY_SP / "pytest" / "__init__.py",
]
print("\n== 最终抽查 ==")
for c in checks:
    print(("EXISTS " if c.exists() else "MISSING"), c)
