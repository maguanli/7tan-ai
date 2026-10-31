# -*- coding: utf-8 -*-
"""验证两处改动：
   A) tool_executor 等待上限：独占 60s / 路径 120s
   B) browser_tools._active_ctx 按 owner 隔离（含单 Agent 跨线程留存回归）
"""
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import contextvars

sys.path.insert(0, r"D:\7tan\7tanAI")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PASS = FAIL = 0


def ck(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {extra}")


# ── A. 等待上限 ──────────────────────────────────────────────────────
import src.agent.tool_executor as te

ck("A1 browser 等 60s", te._timeout_for("browser") == 60.0, te._timeout_for("browser"))
ck("A2 desktop 等 60s", te._timeout_for("desktop") == 60.0)
ck("A3 camera 等 60s", te._timeout_for("camera") == 60.0)
ck("A4 file: 等 120s", te._timeout_for(r"file:d:\a.txt") == 120.0)
ck("A5 git: 等 120s", te._timeout_for(r"git:d:\repo") == 120.0)

# 真的会按时超时（把上限临时调到 1s）
te._EXCLUSIVE_TIMEOUT = 1.0
te._lease.acquire("browser", "holder-X", timeout=1)
t0 = time.time()
try:
    with te._lease.guard("browser", "waiter-Y", timeout=te._timeout_for("browser")):
        ck("A6 不该拿到租约", False)
except te._lease.LeaseTimeout:
    waited = time.time() - t0
    ck(f"A7 1s 后按时超时（实际 {waited:.2f}s）", 0.9 <= waited <= 2.5)
te._lease.release_all("holder-X")
te._EXCLUSIVE_TIMEOUT = 60.0

# ── B. 浏览器上下文隔离 ───────────────────────────────────────────────
import src.tools.browser_tools as bt
from src.utils import exec_context as ec

bt._switch_ui_callback = None

# 主 Agent 设 source
bt.set_active_context("source")
ck("B1 主 Agent 读回 source", bt.get_active_context() == "source")

# Worker A 切 admin
ctx, tok, prev = ec.bind(root=r"D:\7tan\7tanAI", worker_id="w-A")
try:
    bt.set_active_context("admin")
    ck("B2 Worker A 读回 admin", bt.get_active_context() == "admin")
finally:
    ec.unbind(tok, prev)

# 主 Agent 必须还是 source —— 这是本次修的 bug
ck("B3 主 Agent 未被 Worker 覆盖（旧实现会变 admin）",
   bt.get_active_context() == "source", bt.get_active_context())

# Worker B 独立
ctx, tok, prev = ec.bind(root=r"D:\7tan\7tanAI", worker_id="w-B")
try:
    ck("B4 Worker B 看到默认 source", bt.get_active_context() == "source")
    bt.set_active_context("admin")
finally:
    ec.unbind(tok, prev)
ck("B5 B 结束后主 Agent 仍是 source", bt.get_active_context() == "source")

# reset 清理
bt.reset_active_context("w-A")
ck("B6 reset 后 w-A 记录已删", "w-A" not in bt._ctx_by_owner, list(bt._ctx_by_owner))
ck("B7 reset 不动别人的记录", bt._ctx_by_owner.get("w-B") == "admin")

# ── B8/B9 单 Agent 跨线程留存（关键回归）────────────────────────────
# 工具在池线程执行：在池线程里 set 的值，下一次池线程调用必须还看得见。
bt.reset_active_context("main")
bt.set_active_context("source")


def _in_pool_switch():
    bt.set_active_context("admin")
    return bt.get_active_context()


def _in_pool_read():
    return bt.get_active_context()


with ThreadPoolExecutor(max_workers=1) as pool:
    v1 = pool.submit(contextvars.copy_context().run, _in_pool_switch).result()
    v2 = pool.submit(contextvars.copy_context().run, _in_pool_read).result()
ck("B8 池线程里 set 生效", v1 == "admin", v1)
ck("B9 下一次池线程调用仍读到 admin（ContextVar 方案会读回 source）",
   v2 == "admin", v2)

# 无效 owner 兜底
bt._ctx_by_owner.clear()
ck("B10 空表时兜底 source", bt.get_active_context() == "source")

# 视图选择
class FakeView:
    def __init__(self, n): self.n = n
    def __repr__(self): return f"<{self.n}>"

bt._source_view = FakeView("source-view")
bt._admin_view = FakeView("admin-view")
bt.reset_active_context("main")
bt.set_active_context("source")
ck("B11 source 时返回源站视图", bt._get_active_view() is bt._source_view)
bt.set_active_context("admin")
ck("B12 admin 时返回后台视图", bt._get_active_view() is bt._admin_view)

# 并发压测：两线程各 200 轮 set+read，不得串味
errors = []


def _hammer(wid, val):
    ctx, tok, prev = ec.bind(root=r"D:\7tan\7tanAI", worker_id=wid)
    try:
        for _ in range(200):
            bt.set_active_context(val)
            got = bt.get_active_context()
            if got != val:
                errors.append((wid, val, got))
    finally:
        ec.unbind(tok, prev)


ts = [threading.Thread(target=_hammer, args=("w-P1", "admin")),
      threading.Thread(target=_hammer, args=("w-P2", "source"))]
[t.start() for t in ts]
[t.join() for t in ts]
ck(f"B13 并发 400 轮零串味（错误 {len(errors)} 条）", not errors, errors[:3])

print(f"\n[RESULT] 通过 {PASS} / 失败 {FAIL}")
sys.exit(1 if FAIL else 0)
