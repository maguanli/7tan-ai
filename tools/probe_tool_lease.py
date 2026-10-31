# -*- coding: utf-8 -*-
"""验证 tool_executor 的资源排队接入是否正确。

分两块：
  ① 映射：哪些工具该排队、排到哪个资源键
  ② 端到端：两个 Worker 同时调 browse_page，第二个应被拒（而不是悄悄操作错窗口）
"""
import sys
import threading
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import tool_executor as TE
from src.utils import resource_lease as L
from src.utils import exec_context as EC

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ✅ " if ok else "  ❌ ") + name + (("  " + str(detail)) if detail else ""))


def section(t):
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


section("1  工具 → 资源键 映射")
cases = [
    ("browse_page", {}, "browser", True),
    ("click_element", {}, "browser", True),
    ("browser_exec_js", {}, "browser", True),
    ("write_file", {"path": "data/a.txt"}, None, False),       # 动态，下面单独断言
    ("git_add", {"repo_path": "."}, None, False),              # 动态
    ("read_file_content", {"path": "data/a.txt"}, None, False),
    ("run_command", {"command": "dir"}, None, False),
    ("memory_store", {"key": "x"}, None, False),
]
for name, args, want, want_sticky in cases:
    res, sticky = TE.resource_of(name, args)
    if want is None:
        print(f"     {name:20s} -> {res}  sticky={sticky}")
        continue
    check(f"{name} → {want}（sticky={want_sticky}）",
          res == want and sticky == want_sticky, f"实际 {res}/{sticky}")

r1, s1 = TE.resource_of("write_file", {"path": "data/a.txt"})
check("write_file 按绝对路径排队", r1 and r1.startswith("file:"), r1)
check("write_file 不是粘性", s1 is False, s1)

r2, _ = TE.resource_of("git_add", {"repo_path": "."})
check("git 写操作按仓库根排队", r2 and r2.startswith("git:"), r2)

# 同一文件两次调用必须得到同一个键（否则排队形同虚设）
r3, _ = TE.resource_of("write_file", {"path": str(ROOT / "data" / "a.txt")})
check("同一文件的相对/绝对路径归一到同一个键", r1 == r3, f"{r1} vs {r3}")

# 不同文件必须不同键（否则过度串行）
r4, _ = TE.resource_of("write_file", {"path": "data/b.txt"})
check("不同文件得到不同键", r1 != r4, f"{r1} vs {r4}")


section("2  端到端：两个 Worker 抢浏览器")
# 把真实 execute_tool 换成假实现，避免真的去动 Qt 浏览器
calls = []
_orig_exec = TE.execute_tool


def fake_execute(name, args):
    calls.append((EC.owner(), name, round(time.time(), 2)))
    time.sleep(0.6)
    return f"fake {name} by {EC.owner()}"


TE.execute_tool = fake_execute
try:
    out = {}
    old_to = TE._DEFAULT_TIMEOUT
    TE._DEFAULT_TIMEOUT = 0.6            # 缩短等待，便于观察被拒

    def worker(wid, hold_after=0.0):
        # 模拟 spawn_worker 里做的事：绑定上下文 + 压作用域
        ctx, tok, prev = EC.bind(str(ROOT), label=wid, worker_id=wid)
        try:
            out[wid] = TE._execute_tool_optimized("browse_page", {"url": "https://x"})
            if hold_after:
                time.sleep(hold_after)   # 模拟 Worker 还在跑别的步骤
        finally:
            EC.unbind(tok, prev)
            L.release_all(wid)

    ta = threading.Thread(target=worker, args=("w-A", 1.5))
    tb = threading.Thread(target=worker, args=("w-B",))
    ta.start(); time.sleep(0.15); tb.start()
    ta.join(30); tb.join(30)
    TE._DEFAULT_TIMEOUT = old_to

    a, b = out.get("w-A", ""), out.get("w-B", "")
    print(f"     w-A: {a[:70]}")
    print(f"     w-B: {b[:70]}")
    check("第一个 Worker 正常执行", "fake browse_page" in a, a[:50])
    check("第二个被拒且说明原因", "资源繁忙" in b and "browser" in b, b[:60])
    check("被拒时没有真正执行工具", len(calls) == 1, f"实际执行 {len(calls)} 次")
    check("被拒信息含持有人", "w-A" in b, "")
finally:
    TE.execute_tool = _orig_exec
    L.release_all("w-A"); L.release_all("w-B")


section("3  主 Agent 行为不变（不该被 Worker 的粘性租约误伤）")
_orig_exec = TE.execute_tool
TE.execute_tool = lambda n, a: "ok-main"
try:
    v = TE._execute_tool_optimized("browse_page", {"url": "https://x"})
    check("主 Agent 调用浏览器正常返回", v == "ok-main", v)
    check("主 Agent 用完即放（无残留租约）", not L.status(), str(L.status()))
finally:
    TE.execute_tool = _orig_exec


section("4  排队失败时给出的是可读提示，不是异常")
_orig_exec = TE.execute_tool
TE.execute_tool = lambda n, a: "ok"
try:
    held = L.acquire("desktop", "w-BLOCK", sticky=True)
    old = TE._DEFAULT_TIMEOUT
    TE._DEFAULT_TIMEOUT = 0.3
    try:
        msg = TE._execute_tool_optimized("desktop_click", {"x": 1, "y": 1})
    finally:
        TE._DEFAULT_TIMEOUT = old
        L.release(held)
    check("返回字符串而非抛异常", isinstance(msg, str), type(msg).__name__)
    check("提示含资源名与占用者", "desktop" in msg and "w-BLOCK" in msg, msg[:70])
finally:
    TE.execute_tool = _orig_exec


section(f"汇总：{len(PASS)} 通过 / {len(FAIL)} 未通过")
if FAIL:
    print("未通过：" + "，".join(FAIL))
sys.exit(0 if not FAIL else 1)
