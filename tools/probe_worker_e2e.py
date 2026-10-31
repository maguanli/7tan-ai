# -*- coding: utf-8 -*-
"""真实端到端：跑一次 spawn_worker，检查上下文与租约没有泄漏。"""
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import resource_lease as L
from src.utils import cmd_scope as C
from src.utils import exec_context as EC

import importlib.util
spec = importlib.util.spec_from_file_location(
    "spawner", str(ROOT / "data" / "plugins" / "agent_spawner" / "tools.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print("=" * 70)
print("跑一个真实 Worker（简单任务，验证上下文/租约/作用域都能正确复位）")
print("=" * 70)
out = m.spawn_worker(task="只回答一个数字：3+4 等于几。不要调用任何工具。",
                     max_iterations=4, timeout_seconds=180)
print(str(out)[:800])

print()
print("=" * 70)
print("收尾检查")
print("=" * 70)
checks = []
st = L.status()
checks.append(("无租约泄漏", not st, st))
sc = C.current()
checks.append(("作用域帧已弹出", sc is None, sc))
checks.append(("执行上下文已复位（非 Worker）", not EC.is_worker(), EC.current()))
checks.append(("owner 回到 main", EC.owner() == "main", EC.owner()))
checks.append(("串行闸门已释放", not m._STATE.get("running"), m._STATE))

bad = 0
for name, ok, detail in checks:
    print(("  OK   " if ok else "  FAIL ") + name + (f"   {detail}" if not ok else ""))
    if not ok:
        bad += 1
print()
print("结论：" + ("全部复位正常" if bad == 0 else f"{bad} 项未复位"))
sys.exit(0 if bad == 0 else 1)
