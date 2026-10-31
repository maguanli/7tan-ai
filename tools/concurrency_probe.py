# -*- coding: utf-8 -*-
"""多任务并发冲突探针。

目的：在真的开并发之前，先把「哪些东西会打架、打架时是什么现象」量出来。
分三层：
    L1 机制层   abort_signal / cmd_scope / 审计落盘 —— 纯线程，不花钱
    L2 闸门层   spawn_worker 的串行锁在并发下是否真的只放一个
    L3 资源层   同一文件写、同一仓库 git、浏览器单例 —— 真冲突在哪

用法：
    python tools/concurrency_probe.py            # 只跑 L1 + L2
    python tools/concurrency_probe.py --live     # 追加 L3 的真实 LLM 并发
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULT = []
LOCK = threading.Lock()


def rec(name, ok, detail=""):
    detail = "" if detail is None else str(detail)
    with LOCK:
        RESULT.append((name, ok, detail))
        print(("  ✅ " if ok else "  ❌ ") + name + (("  " + detail) if detail else ""))


def section(t):
    print("\n" + "=" * 68)
    print(t)
    print("=" * 68)


# ══════════════════════════════════════════════════════════
# L1-1  abort_signal 跨线程隔离
# ══════════════════════════════════════════════════════════
def l1_abort():
    section("L1-1  abort_signal：4 线程各自注册，只置位其中一个")
    from src.utils import abort_signal as A

    sigs, verdicts = {}, {}
    barrier = threading.Barrier(4)

    def work(idx):
        s = threading.Event()
        sigs[idx] = s
        A.register(s)
        try:
            barrier.wait(timeout=10)
            if idx == 2:
                s.set()
            time.sleep(0.25)
            verdicts[idx] = A.is_aborted()
        finally:
            A.unregister(s)

    ts = [threading.Thread(target=work, args=(i,), name=f"abort-t{i}") for i in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(20)

    rec("线程 2 置位后，自己判 True", verdicts.get(2) is True, f"is_aborted={verdicts.get(2)}")
    others = [i for i in (0, 1, 3) if verdicts.get(i) is not False]
    rec("其余 3 线程不受连累（全 False）", not others,
        "" if not others else f"被连累的线程: {others} → {[verdicts[i] for i in others]}")

    # 嵌套污染：同线程内层置位，弹出后外层恢复
    outer = threading.Event()
    A.register(outer)
    try:
        inner = threading.Event()
        A.register(inner)
        inner.set()
        v_inner = A.is_aborted()
        A.unregister(inner)
        v_after = A.is_aborted()
    finally:
        A.unregister(outer)
    rec("嵌套：内层置位时判 True", v_inner is True)
    rec("嵌套：内层注销后外层恢复 False", v_after is False, f"恢复后={v_after}")


# ══════════════════════════════════════════════════════════
# L1-2  cmd_scope 跨线程隔离 + 线程池失帧
# ══════════════════════════════════════════════════════════
def l1_scope():
    section("L1-2  cmd_scope：4 线程各压不同根目录，互相不可见")
    from src.utils import cmd_scope as C

    own_root = {i: (ROOT / f"_probe_root_{i}") for i in range(4)}
    outs, barrier = {}, threading.Barrier(4)

    def work(idx):
        for r in own_root.values():
            r.mkdir(parents=True, exist_ok=True)
        f = C.push(own_root[idx], label=f"w{idx}", strict=True)
        try:
            barrier.wait(timeout=10)
            time.sleep(0.2)
            # 自己的根：应放行
            try:
                C.resolve_cwd(str(own_root[idx])); mine_ok = True
            except C.ScopeViolation:
                mine_ok = False
            # 别人的根：应拒绝
            other = own_root[(idx + 1) % 4]
            try:
                C.resolve_cwd(str(other)); cross_blocked = False
            except C.ScopeViolation:
                cross_blocked = True
            seen = C.current()
            outs[idx] = (mine_ok, cross_blocked, str(seen.root) if seen else None)
        finally:
            C.pop(f)

    ts = [threading.Thread(target=work, args=(i,), name=f"scope-t{i}") for i in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(20)

    rec("每线程自己的根都放行", all(v[0] for v in outs.values()))
    rec("跨线程根全部拒绝（帧不串）", all(v[1] for v in outs.values()))
    correct = all(os.path.normcase(v[2]) == os.path.normcase(str(own_root[i].resolve()))
                  for i, v in outs.items())
    rec("每线程看到的是自己的帧", correct,
        "" if correct else str({i: v[2] for i, v in outs.items()}))

    # 跨线程池：必须显式带上下文，否则丢帧（这是 Python 的既定行为）
    import contextvars
    from concurrent.futures import ThreadPoolExecutor
    box = {}

    def in_pool_naive():
        box["naive_frame"] = C.current()
        try:
            C.resolve_cwd(str(ROOT / "src")); box["naive_escape"] = True
        except C.ScopeViolation:
            box["naive_escape"] = False

    def in_pool_ctx():
        box["ctx_frame"] = C.current()
        try:
            C.resolve_cwd(str(ROOT / "src")); box["ctx_escape"] = True
        except C.ScopeViolation:
            box["ctx_escape"] = False

    f = C.push(own_root[0], label="push-in-main", strict=True)
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(in_pool_naive).result(timeout=10)
        with ThreadPoolExecutor(max_workers=1) as ex:
            _ctx = contextvars.copy_context()
            ex.submit(_ctx.run, in_pool_ctx).result(timeout=10)
    finally:
        C.pop(f)

    rec("裸提交（不 copy_context）会丢帧 —— 调用方必须自己带上下文",
        box.get("naive_frame") is None and box.get("naive_escape") is True,
        f"frame={box.get('naive_frame')} 越界放行={box.get('naive_escape')}")
    rec("copy_context 提交后帧与围栏都恢复",
        box.get("ctx_frame") is not None and box.get("ctx_escape") is False,
        f"frame={getattr(box.get('ctx_frame'), 'label', None)} 越界放行={box.get('ctx_escape')}")


# ══════════════════════════════════════════════════════════
# L1-3  审计落盘在并发下是否损坏
# ══════════════════════════════════════════════════════════
def l1_audit():
    section("L1-3  审计 JSONL：8 线程 × 25 条并发写")
    from src.utils import cmd_scope as C

    p = C.audit_path() if callable(getattr(C, "audit_path", None)) else None
    p = Path(p) if p else (ROOT / "data" / "logs" / "cmd_audit.jsonl")
    before = p.stat().st_size if p.exists() else 0

    N_T, N_W = 8, 25
    marker = f"probe{int(time.time())}"
    errs = []

    def work(ti):
        for i in range(N_W):
            try:
                C.audit(tool="probe", command=f"echo {marker}-{ti}-{i}",
                        cwd=str(ROOT), rc=0, duration_ms=1,
                        extra={"scope": f"probe{ti}"})
            except Exception as e:
                errs.append(f"{type(e).__name__}: {e}")

    ts = [threading.Thread(target=work, args=(i,), name=f"audit-t{i}") for i in range(N_T)]
    t0 = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    dt = time.time() - t0

    rec(f"{N_T*N_W} 条写入无异常", not errs, "" if not errs else errs[:3])

    # 校验：从 before 偏移开始读，逐行必须都是合法 JSON
    bad, mine = 0, 0
    try:
        with open(p, "rb") as f:
            f.seek(before)
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    o = json.loads(raw.decode("utf-8"))
                    if marker in str(o.get("command", "")):
                        mine += 1
                except Exception:
                    bad += 1
    except FileNotFoundError:
        pass

    rec("并发写入后无半行/撕裂记录", bad == 0, f"损坏行={bad}")
    rec(f"本批 {N_T*N_W} 条全部落地可解析", mine == N_T * N_W, f"实际读到={mine}")
    print(f"     耗时 {dt:.2f}s，文件 {p}")


# ══════════════════════════════════════════════════════════
# L1-4  同一文件并发写：读-改-写丢更新
# ══════════════════════════════════════════════════════════
def l1_lost_update():
    section("L1-4  同一文件并发读-改-写：会不会丢更新")
    tmp = ROOT / "data" / "_probe_counter.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("0", encoding="utf-8")

    ROUNDS, THREADS = 40, 8

    def naive():
        for _ in range(ROUNDS):
            n = int(tmp.read_text(encoding="utf-8") or 0)
            time.sleep(0.0005)           # 放大竞态窗口，模拟真实 LLM 思考耗时
            tmp.write_text(str(n + 1), encoding="utf-8")

    ts = [threading.Thread(target=naive) for _ in range(THREADS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    got = int(tmp.read_text(encoding="utf-8") or 0)
    expect = ROUNDS * THREADS
    lost = expect - got

    rec("【冲突复现】朴素读-改-写丢更新", lost > 0,
        f"期望 {expect}，实际 {got}，丢失 {lost} 条 ({lost/expect*100:.0f}%)")

    # 加锁版
    tmp.write_text("0", encoding="utf-8")
    flock = threading.Lock()

    def locked():
        for _ in range(ROUNDS):
            with flock:
                n = int(tmp.read_text(encoding="utf-8") or 0)
                tmp.write_text(str(n + 1), encoding="utf-8")

    ts = [threading.Thread(target=locked) for _ in range(THREADS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    got2 = int(tmp.read_text(encoding="utf-8") or 0)
    rec("加锁后无丢失", got2 == expect, f"实际 {got2}/{expect}")
    tmp.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# L1-5  同一仓库并发 git
# ══════════════════════════════════════════════════════════
def l1_git():
    section("L1-5  同一仓库并发 git 命令：index.lock 冲突")
    repo = ROOT
    if not (repo / ".git").exists():
        rec("仓库存在", False, "未找到 .git")
        return

    def run(cmd):
        try:
            r = subprocess.run(cmd, cwd=str(repo), capture_output=True,
                               text=True, timeout=40, shell=True)
            return r.returncode, (r.stderr or "")[:200]
        except subprocess.TimeoutExpired:
            return -1, "timeout"

    N = 6
    out = [None] * N

    def work(i):
        out[i] = run("git status --porcelain")

    ts = [threading.Thread(target=work, args=(i,)) for i in range(N)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    lock_hits = [x for x in out if x and ("index.lock" in x[1] or "another git process" in x[1])]
    rec("并发 git status（只读）不出锁冲突", not lock_hits,
        f"{len(lock_hits)}/{N} 命中 index.lock" if lock_hits else "")

    # 写操作：git add + reset 反复
    def work_w(i):
        for _ in range(6):
            run("git add -A")
            run("git reset -q")

    out2 = []
    def work_w2(i):
        for _ in range(6):
            out2.append(run("git add -A"))

    ts = [threading.Thread(target=work_w2, args=(i,)) for i in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(90)
    wl = [x for x in out2 if x and ("index.lock" in x[1] or "Unable to create" in x[1])]
    rec("【冲突复现】并发 git 写操作会撞 index.lock", len(wl) > 0,
        f"{len(wl)}/{len(out2)} 次失败" if wl else "本次未复现（概率性）")
    run("git reset -q")


# ══════════════════════════════════════════════════════════
# L2  spawn_worker 串行闸门
# ══════════════════════════════════════════════════════════
def l2_gate():
    section("L2  串行闸门：5 个 spawn_worker 同时到达，只应放行 1 个")
    import importlib.util
    p = ROOT / "data" / "plugins" / "agent_spawner" / "tools.py"
    spec = importlib.util.spec_from_file_location("spawner_probe", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        rec("插件可导入", False, f"{type(e).__name__}: {e}")
        return

    rec("插件可导入", True)
    has_lock = hasattr(mod, "_RUN_LOCK") and isinstance(mod._RUN_LOCK, type(threading.Lock()))
    rec("存在串行锁 _RUN_LOCK", has_lock)

    # 直接测锁语义：非阻塞抢锁，5 线程只有 1 个成功
    results, barrier = [], threading.Barrier(5)

    def try_lock(i):
        barrier.wait(timeout=10)
        got = mod._RUN_LOCK.acquire(blocking=False)
        with LOCK:
            results.append((i, got))
        if got:
            time.sleep(0.4)
            mod._RUN_LOCK.release()

    ts = [threading.Thread(target=try_lock, args=(i,)) for i in range(5)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(20)

    winners = [i for i, g in results if g]
    losers = [i for i, g in results if not g]
    rec("并发抢锁只放行 1 个", len(winners) == 1,
        f"拿到锁={winners} 被拒={losers}")

    # 状态结构
    st = getattr(mod, "_STATE", None)
    rec("_STATE 记录 running/worker_id", isinstance(st, dict) and "running" in st,
        f"keys={list(st.keys()) if isinstance(st, dict) else None}")


# ══════════════════════════════════════════════════════════
# L3  共享资源单例（浏览器 / 桌面）
# ══════════════════════════════════════════════════════════
def l3_singletons():
    section("L3-1  浏览器 / 桌面：进程级单例，并发时只有一份")
    try:
        import src.tools.browser_tools as B
    except Exception as e:
        rec("browser_tools 可导入", False, f"{type(e).__name__}: {e}")
        return

    # 已知的模块级可变状态（browser_tools.py:15-18）
    KNOWN = ["_source_view", "_admin_view", "_active_ctx", "_switch_ui_callback"]
    present = [n for n in KNOWN if hasattr(B, n)]
    print(f"     已知模块级状态：{present}")
    rec("找到浏览器模块级状态变量", len(present) >= 3, f"{present}")

    # 两个线程读到的是不是同一份
    box = {}
    def probe(tag):
        box[tag] = {n: id(getattr(B, n)) for n in present}

    t1 = threading.Thread(target=probe, args=("a",))
    t2 = threading.Thread(target=probe, args=("b",))
    t1.start(); t2.start(); t1.join(10); t2.join(10)

    shared = sum(1 for n in present
                 if box.get("a", {}).get(n) is not None
                 and box["a"][n] == box.get("b", {}).get(n))
    rec("【冲突源】浏览器状态跨线程同一实例（非线程私有）",
        shared == len(present),
        f"{shared}/{len(present)} 个（id 相同）")

    # ── 真实冲突复现：_active_ctx 被别的 Worker 切走 ──
    if hasattr(B, "_active_ctx") and hasattr(B, "set_active_context"):
        orig = B._active_ctx
        log = []
        gate = threading.Barrier(2)

        def worker_a():
            B.set_active_context("source")
            gate.wait(timeout=10)
            time.sleep(0.15)                       # A 以为自己在操作源站
            log.append(("A", "期望 source", getattr(B, "_active_ctx", None)))

        def worker_b():
            gate.wait(timeout=10)
            B.set_active_context("admin")          # B 把全局上下文切到后台
            log.append(("B", "设置 admin", getattr(B, "_active_ctx", None)))

        ta = threading.Thread(target=worker_a); tb = threading.Thread(target=worker_b)
        ta.start(); tb.start(); ta.join(20); tb.join(20)
        B._active_ctx = orig

        a = [x for x in log if x[0] == "A"]
        wrong = bool(a) and a[0][2] != "source"
        rec("【冲突复现】A 的浏览器上下文被 B 切走",
            wrong, f"A 末尾看到 _active_ctx={a[0][2] if a else '?'}（A 自己设的是 source）")
    else:
        rec("set_active_context 存在", False, "接口缺失，跳过上下文冲突复现")

    # 模块内没有锁 —— 但防护放在统一入口 tool_executor，不在这里。
    # 检查的是"有没有被租约覆盖"，而不是"模块里有没有 threading.Lock"。
    locks = [n for n in dir(B) if "lock" in n.lower()]
    try:
        from src.agent.tool_executor import resource_of
        res, sticky = resource_of("browse_page", {})
        rec("浏览器工具已被租约覆盖（入口处排队）",
            res == "browser" and sticky is True,
            f"模块内锁={locks or '无'}；入口租约={res}/sticky={sticky}")
    except Exception as e:
        rec("浏览器工具已被租约覆盖", False, f"{type(e).__name__}: {e}")

    # 桌面工具是插件，不是 src/tools 模块
    plug = ROOT / "data" / "plugins" / "desktop_bot" / "tools.py"
    if plug.exists():
        src_txt = plug.read_text(encoding="utf-8", errors="replace")
        has_lock = ("threading.Lock" in src_txt) or ("threading.RLock" in src_txt)
        try:
            from src.agent.tool_executor import resource_of
            res, sticky = resource_of("desktop_click", {})
            rec("桌面工具已被租约覆盖（入口处排队）",
                res == "desktop" and sticky is True,
                f"插件内锁={has_lock}；入口租约={res}/sticky={sticky}")
        except Exception as e:
            rec("桌面工具已被租约覆盖", False, f"{type(e).__name__}: {e}")
    else:
        cands = [p.name for p in (ROOT / "data" / "plugins").glob("*desk*")]
        rec("找到桌面插件目录", bool(cands), f"{cands}" if cands else "未找到")


# ══════════════════════════════════════════════════════════
# L3-2  真实 LLM 并发（可选，花钱）
# ══════════════════════════════════════════════════════════
def l3_live(n=2):
    section(f"L3-2  真实并发：{n} 个 run_agent_loop 同时跑")
    from src.agent.agent_loop import run_agent_loop
    from src.tools.registry import get_all_tools

    tools = get_all_tools() or []
    qs = ["只回答一个数字：1+1 等于几？", "只回答一个数字：2+2 等于几？",
          "只回答一个数字：3+3 等于几？"][:n]
    outs, errs = {}, {}

    def work(i, q):
        t0 = time.time()
        try:
            r = run_agent_loop(task=q, tools=tools,
                               session_id=f"probe-conc-{i}-{int(time.time())}",
                               max_iterations=3,
                               abort_event=threading.Event())
            outs[i] = {"ans": str(r.get("answer", r.get("result", "")))[:80],
                       "it": r.get("iterations"), "dt": round(time.time() - t0, 1)}
        except Exception as e:
            errs[i] = f"{type(e).__name__}: {e}"

    ts = [threading.Thread(target=work, args=(i, q), name=f"live-{i}")
          for i, q in enumerate(qs)]
    t0 = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join(300)
    wall = time.time() - t0

    rec(f"{n} 个并发全部返回", not errs, "" if not errs else str(errs))
    for i in sorted(outs):
        print(f"     worker{i}: {outs[i]}")
    if len(outs) >= 2:
        rec("各 Worker 答案互不相同（未串话）",
            len({v["ans"].strip() for v in outs.values()}) == len(outs),
            f"distinct={len({v['ans'].strip() for v in outs.values()})}/{len(outs)}")
    print(f"     并行墙钟 {wall:.1f}s")


def main():
    live = "--live" in sys.argv
    print(f"项目根 {ROOT}")
    print(f"并发探针开始 {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for fn in (l1_abort, l1_scope, l1_audit, l1_lost_update, l1_git, l2_gate, l3_singletons):
        try:
            fn()
        except Exception:
            rec(fn.__name__ + " 执行异常", False, traceback.format_exc()[-300:])

    if live:
        try:
            l3_live(2)
        except Exception:
            rec("l3_live 执行异常", False, traceback.format_exc()[-300:])

    section("汇总")
    ok = sum(1 for _, o, _ in RESULT if o)
    bad = len(RESULT) - ok
    print(f"  断言 {len(RESULT)} 项：通过 {ok}，未通过 {bad}")
    if bad:
        print("  未通过清单：")
        for n, o, d in RESULT:
            if not o:
                print(f"    · {n}  {d}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
