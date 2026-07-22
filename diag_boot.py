"""启动诊断脚本：逐步导入关键模块，定位崩溃点"""
import sys, traceback
sys.path.insert(0, '.')

steps = [
    ("utils.retry", "from src.utils import retry"),
    ("agent.model_manager", "from src.agent import model_manager"),
    ("tools.registry", "from src.tools import registry"),
    ("config.loader", "from src.config import loader"),
    ("database.db", "from src.database import db"),
    ("ui.app", "from src.ui import app"),
]

for name, code in steps:
    try:
        exec(code, {})
        print(f"[OK] {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        traceback.print_exc()
        break
