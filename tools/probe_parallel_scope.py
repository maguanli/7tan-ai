# -*- coding: utf-8 -*-
"""验证：agent_loop 并行路径 / 看门狗路径下，cmd_scope 作用域是否还在。

背景：
    2026-11-01 发现 agent_optimizer 把工具丢进 ThreadPoolExecutor，
    threading.local 的帧在池线程里丢失 → 越界命令被放行。
    修法：cmd_scope 改用 ContextVar + agent_optimizer 提交时 copy_context().run()。

本脚本走【真实调用链】验证，而不是直接往池里丢任务（那样测不出修复）。
"""
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import cmd_scope as C
from src.agent.agent_optimizer import (
    execute_tools_parallel, _execute_with_watchdog, _should_parallel,
)

sandbox = ROOT / "_probe_scope_zone"
sandbox.mkdir(exist_ok=True)
outside = ROOT / "tools"

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ✅ " if ok else "  ❌ ") + name + (("  " + str(detail)) if detail else ""))


def report_exec(name, args=None, label=""):
    """伪工具执行函数：回显它被哪个线程跑、看得到什么帧、越界能不能过。"""
    import threading
    f = C.current()
    try:
        C.resolve_cwd(str(outside))
        escape = "放行"
    except C.ScopeViolation:
        escape = "拒绝"
    return (f"label={label or name} thread={threading.current_thread().name} "
            f"frame={(f.label if f else None)} escape={escape}")


print("=" * 70)
print("证 1：并行判定确实会走线程池")
print("=" * 70)
calls = [
    {"id": "c1", "function": {"name": "write_file", "arguments": "{}"}},
    {"id": "c2", "function": {"name": "run_command", "arguments": "{}"}},
]
print(f"  _should_parallel = {_should_parallel(calls)}")

print()
print("=" * 70)
print("证 2：作用域内并行执行，池线程能否看到帧")
print("=" * 70)
frame = C.push(sandbox, label="probe-worker", strict=True)
try:
    res = execute_tools_parallel(calls, report_exec)
    for r in res:
        print("     " + r["content"])

    contents = [r["content"] for r in res]
    check("并行路径：池线程看得到作用域帧",
          all("frame=probe-worker" in c for c in contents),
          str(contents[0])[:100] if "frame=None" in contents[0] else "")
    check("并行路径：越界命令被拒绝（不再 fail-open）",
          all("escape=拒绝" in c for c in contents))

    print()
    print("=" * 70)
    print("证 3：看门狗路径（单工具串行也走它）")
    print("=" * 70)
    out = _execute_with_watchdog(report_exec, "some_tool", {}, timeout=20)
    print("     " + str(out))
    check("看门狗路径：帧不丢", "frame=probe-worker" in str(out))
    check("看门狗路径：越界被拒绝", "escape=拒绝" in str(out))
finally:
    C.pop(frame)

print()
print("=" * 70)
print("证 4：Worker 结束后，主 Agent 恢复宽松语义（不误伤）")
print("=" * 70)
out2 = _execute_with_watchdog(report_exec, "some_tool", {}, timeout=20)
print("     " + str(out2))
check("Worker 结束后主 Agent 无帧（宽松）", "frame=None" in str(out2))
check("Worker 结束后主 Agent 可访问任意目录", "escape=放行" in str(out2))

print()
print("=" * 70)
print(f"断言 {len(PASS)+len(FAIL)} 项：通过 {len(PASS)}，未通过 {len(FAIL)}")
if FAIL:
    print("未通过：" + "，".join(FAIL))
sys.exit(0 if not FAIL else 1)
