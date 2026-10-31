# -*- coding: utf-8 -*-
"""remote_deployer 审计/作用域接入自检（正向 + 反向）"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.utils import cmd_scope  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (f"  [{detail}]" if detail and not cond else ""))


spec = importlib.util.spec_from_file_location(
    "plug_remote", ROOT / "data" / "plugins" / "remote_deployer" / "tools.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

print("=== 正向：作用域内执行 + 留痕 ===")
sub = (ROOT / "data").resolve()
fr = cmd_scope.push(sub, label="w-remote", strict=True)

r = rd.run_shell_script("echo rd-inside", cwd=str(sub), timeout=20)
check("1 run_shell_script 可执行", r.get("success") is True and "rd-inside" in r.get("stdout", ""), str(r)[:160])

rows = cmd_scope.query(limit=5, keyword="echo rd-inside")
check("2 留痕且带工具名", bool(rows) and rows[0].get("tool") == "run_shell_script",
      str(rows[0].get("tool")) if rows else "无记录")
check("3 留痕范围是本作用域", bool(rows) and rows[0].get("scope") == "w-remote",
      str(rows[0].get("scope")) if rows else "无记录")

print("\n=== 反向：越界 cwd 被拒绝 ===")
r2 = rd.run_shell_script("echo rd-outside", cwd=str(ROOT), timeout=20)
check("4 越界被拒绝", r2.get("success") is False and "已拒绝" in r2.get("stderr", ""), str(r2)[:200])
check("5 越界命令未执行", "rd-outside" not in (r2.get("stdout") or ""))
rows2 = cmd_scope.query(limit=5, keyword="echo rd-outside")
check("6 被拒绝也留痕", bool(rows2) and "cwd 越界" in str(rows2[0].get("error")),
      str(rows2[0].get("error")) if rows2 else "无记录")

print("\n=== 反向：失败命令留痕 ===")
r3 = rd.run_shell_script("exit 7", cwd=str(sub), timeout=20)
check("7 非零退出码被记录", r3.get("exit_code") == 7, str(r3)[:120])
rows3 = cmd_scope.query(limit=5, keyword="exit 7")
check("8 审计里有 rc=7", bool(rows3) and rows3[0].get("rc") == 7,
      str(rows3[0].get("rc")) if rows3 else "无记录")

cmd_scope.pop(fr)
check("9 弹帧后恢复宽松",
      cmd_scope.current() is None and rd.run_shell_script("echo loose", cwd=str(ROOT), timeout=20).get("success") is True)

print("\n" + "=" * 50)
print(f"通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
if FAIL:
    print("失败：", FAIL)
sys.exit(0 if not FAIL else 1)
