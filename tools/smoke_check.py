# -*- coding: utf-8 -*-
"""改动文件的编译 + 导入冒烟检查。"""
import py_compile
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CHANGED = [
    "src/utils/exec_context.py",
    "src/utils/resource_lease.py",
    "src/utils/cmd_scope.py",
    "src/agent/agent_optimizer.py",
    "src/agent/tool_executor.py",
    "data/plugins/agent_spawner/tools.py",
    "tools/concurrency_probe.py",
    "tools/probe_lease.py",
    "tools/probe_tool_lease.py",
    "tools/probe_parallel_scope.py",
]

bad = 0
print("编译检查：")
for rel in CHANGED:
    p = ROOT / rel
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"  OK   {rel}")
    except py_compile.PyCompileError as e:
        bad += 1
        print(f"  FAIL {rel}\n       {str(e)[:200]}")

print("\n导入冒烟：")
MODS = [
    "src.agent.agent_loop",
    "src.agent.tool_executor",
    "src.agent.agent_optimizer",
    "src.tools.registry",
    "src.utils.cmd_scope",
    "src.utils.exec_context",
    "src.utils.resource_lease",
    "src.tools.browser_tools",
]
for m in MODS:
    try:
        __import__(m)
        print(f"  OK   {m}")
    except Exception as e:
        bad += 1
        print(f"  FAIL {m}  {type(e).__name__}: {e}")

print("\n" + ("全部正常" if bad == 0 else f"{bad} 处有问题"))
sys.exit(0 if bad == 0 else 1)
