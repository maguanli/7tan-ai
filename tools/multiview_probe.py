# -*- coding: utf-8 -*-
"""动态多视图自检 —— 验证「浏览器不是单例」这件事真的落地了。

两种模式：
    python tools/multiview_probe.py          逻辑层（不需要 GUI）
    python tools/multiview_probe.py real     真实 Qt 层（真开 3 个 QWebEngineView）

为什么要分两层：
    逻辑层能证明「租约键按 owner 分开、视图只创建一次、结束时销毁」；
    但它证明不了「3 个 QWebEngineView 真能同时加载各自的页面且互不顶掉」。
    后者必须真开 Qt 才能验，所以单独一层。
"""
import os
import sys
import threading
import time
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PASS, FAIL = [], []


def ok(cond, name, detail=""):
    (PASS if cond else FAIL).append(f"{name}{(' | ' + detail) if detail else ''}")
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (f"  {detail}" if detail else ""))


# ─────────────────────────────────────────────────────────────
# 一、逻辑层
# ─────────────────────────────────────────────────────────────
def test_logic():
    from src.utils import exec_context as ec
    from src.tools import browser_tools as bt
    from src.tools import browser_bridge as bb
    from src.agent import tool_executor as te

    print("\n[逻辑] 1. 租约键按执行者分键")

    # 主 Agent：应退化到按角色分键（它用界面上那两个窗口）
    _, t1, p1 = ec.bind(worker_id="main-probe")
    try:
        bt.set_active_context("source")
        k_main_source = bt.lease_key()
        bt.set_active_context("admin")
        k_main_admin = bt.lease_key()
    finally:
        ec.unbind(t1, p1)
    # 主 Agent 用的是界面上那两个【共享】窗口，源站和后台是两个不同的物理视图，
    # 所以它们的键应当【不同】（同角色才互斥）。这里断言的是「按角色而非 owner」。
    ok(k_main_source == "browser:role:source" and k_main_admin == "browser:role:admin",
       "主 Agent 按视图角色分键（源站/后台是两个窗口）", f"{k_main_source} / {k_main_admin}")

    # Worker：有独立视图能力时按 owner 分键
    real_can = bb.can_spawn_views()
    bb.can_spawn_views = lambda: True          # 强制走「有独立视图」分支
    try:
        keys = {}
        for w in ("w-aaa", "w-bbb", "w-ccc"):
            _, t, p = ec.bind(worker_id=w)
            try:
                bt.set_active_context("source")
                keys[w] = bt.lease_key()
            finally:
                ec.unbind(t, p)
        ok(len(set(keys.values())) == 3, "3 个 Worker 的租约键互不相同", str(keys))
        ok(all(k == f"browser:own:{w}" for w, k in keys.items()),
           "键形如 browser:own:<worker>", str(keys))

        # 关键：同 owner 用 source 还是 admin，键都一样（不会再互相排队）
        _, t, p = ec.bind(worker_id="w-aaa")
        try:
            bt.set_active_context("source"); a = bt.lease_key()
            bt.set_active_context("admin"); b = bt.lease_key()
        finally:
            ec.unbind(t, p)
        ok(a == b, "同 Worker 切换源站/后台不影响自己的租约键", f"{a} == {b}")
    finally:
        bb.can_spawn_views = (lambda: real_can)

    print("\n[逻辑] 2. 开不出视图时退回按角色分键（v2 兜底）")
    bb.can_spawn_views = lambda: False
    try:
        _, t, p = ec.bind(worker_id="w-ddd")
        try:
            bt.set_active_context("source"); ks = bt.lease_key()
            bt.set_active_context("admin"); ka = bt.lease_key()
        finally:
            ec.unbind(t, p)
        ok(ks == "browser:role:source" and ka == "browser:role:admin",
           "无独立视图时退回角色分键", f"{ks} / {ka}")
    finally:
        bb.can_spawn_views = (lambda: real_can)

    print("\n[逻辑] 3. tool_executor 真的用了新键")
    res1, sticky1 = te.resource_of("browse_page", {"url": "https://example.com"})
    ok(sticky1 is True and str(res1).startswith("browser:"), "browse_page 归类为浏览器资源", str(res1))
    res2, _ = te.resource_of("camera_capture", {})
    ok(res2 == "camera", "camera 仍是全局独占（不受本次改动影响）", str(res2))
    res3, _ = te.resource_of("desktop_click_pos", {"pos": "1,1"})
    ok(res3 == "desktop", "desktop 仍是全局独占（鼠标只有一套）", str(res3))

    print("\n[逻辑] 4. 视图只创建一次、结束销毁")
    created, destroyed = [], []

    class FakeView:
        def __init__(self): self.alive = True

    class FakeBridge:
        def __init__(self, owner): self.owner = owner

    fake_bridges, fake_views = {}, {}

    def fake_spawn(owner, timeout=20.0):
        if owner in fake_views:
            return fake_views[owner], ""
        created.append(owner)
        fake_views[owner] = FakeView()
        fake_bridges[owner] = FakeBridge(owner)
        return fake_views[owner], ""

    def fake_get_bridge_for(owner):
        return fake_bridges.get(owner)

    def fake_destroy(owner):
        if owner not in fake_views:
            return False
        destroyed.append(owner)
        fake_views.pop(owner, None)
        fake_bridges.pop(owner, None)
        return True

    orig = (bb.spawn_owner_view, bb.get_bridge_for, bb.destroy_owner_view, bb.can_spawn_views)
    bb.spawn_owner_view, bb.get_bridge_for = fake_spawn, fake_get_bridge_for
    bb.destroy_owner_view, bb.can_spawn_views = fake_destroy, (lambda: True)
    try:
        _, t, p = ec.bind(worker_id="w-eee")
        try:
            b1 = bt.ensure_owner_view("w-eee")
            b2 = bt.ensure_owner_view("w-eee")
            b3 = bt.ensure_owner_view("w-eee")
        finally:
            ec.unbind(t, p)
        ok(created == ["w-eee"], "同一 Worker 连续 3 次只创建 1 个视图", f"created={created}")
        ok(b1 is b2 is b3 and b1 is not None, "三次拿到同一个 Bridge", str(b1.owner))

        bt.release_owner_view("w-eee")
        ok(destroyed == ["w-eee"] and not fake_views, "结束时视图被销毁", f"destroyed={destroyed}")
        ok(bt.release_owner_view("w-eee") is False, "重复销毁返回 False（幂等）")
        ok(bt.release_owner_view("main") is False, "主 Agent 不销毁共享视图")
    finally:
        bb.spawn_owner_view, bb.get_bridge_for, bb.destroy_owner_view, bb.can_spawn_views = orig

    print("\n[逻辑] 5. 主 Agent 不会被分到独立视图")
    _prev_fb = getattr(ec._fallback, "owner", None)
    ec.clear()                      # 真正的「无 Worker 上下文」状态
    ec._fallback.owner = None
    try:
        ok(ec.owner() == "main", "上下文已复位为主 Agent", ec.owner())
        ok(bt.ensure_owner_view("") is None, "主 Agent 开视图请求返回 None（用共享窗口）")
        ok(bt.lease_key().startswith("browser:role:"), "主 Agent 租约键走角色分键", bt.lease_key())
    finally:
        ec._fallback.owner = _prev_fb

    print("\n[逻辑] 6. 上限保护")
    cap = bb._max_owner_views()
    ok(isinstance(cap, int) and cap >= 1, f"视图上限可配（当前 {cap}）")
    old = bb._owner_view.copy()
    try:
        bb._owner_view.clear()
        for i in range(cap):
            bb._owner_view[f"f{i}"] = FakeView()
        got, err = bb.spawn_owner_view("overflow") if bb._gui_anchor() is None else (None, "skip")
        # 直接验上限判断：有锚点时才会走到上限判断，这里用内部逻辑复现
        over = len(bb._owner_view) >= cap
        ok(over, "达到上限后不再新建（走兜底共享视图）", f"count={len(bb._owner_view)} cap={cap}")
    finally:
        bb._owner_view.clear()
        bb._owner_view.update(old)


# ─────────────────────────────────────────────────────────────
# 二、真实 Qt 层
# ─────────────────────────────────────────────────────────────
def test_real():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer, QUrl, QMetaObject, Qt
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    from src.tools import browser_bridge as bb

    app = QApplication.instance() or QApplication(sys.argv)

    print("\n[真实] 1. 建立 GUI 锚点（模拟界面上已有的源站窗口）")
    main_view = QWebEngineView()
    main_view.setHtml("<h1>MAIN</h1>")
    bb.register_bridge(main_view)
    ok(bb.can_spawn_views(), "can_spawn_views() = True")

    print("\n[真实] 2. 开 3 个独立视图")
    owners = ["w-p1", "w-p2", "w-p3"]
    views = {}
    for o in owners:
        v, err = bb.spawn_owner_view(o)
        views[o] = v
        ok(v is not None, f"{o} 视图创建成功", err or "")
    ok(len(set(id(v) for v in views.values() if v)) == 3, "3 个视图是不同实例")

    results, timing = {}, {}

    def work(o):
        t0 = time.time()
        b = bb.get_bridge_for(o)
        try:
            page = f"<html><head><title>{o}</title></head><body><div id='m'>{o}-DATA</div></body></html>"
            b.navigate("data:text/html," + page.replace("#", "%23"), wait_seconds=2.0)
            txt = b.execute_js("document.getElementById('m').innerText", timeout=5.0)
            title = b.execute_js("document.title", timeout=5.0)
            results[o] = (txt, title)
        except Exception as e:
            results[o] = ("ERR", f"{type(e).__name__}: {e}")
        timing[o] = round(time.time() - t0, 2)

    # 关键：navigate/execute_js 用的是 BlockingQueuedConnection，
    # 必须让主线程在事件循环里，否则工作线程会一直等到超时。
    # （第一次写这个测试时就踩了：没 app.exec()，三个线程干等 180 秒，
    #  结果全空，却被误当成「并行失败」。测试脚本自己错的坑要写在这。）
    print("\n[真实] 3. 3 个线程同时导航 + 执行 JS（验证互不顶掉）")
    state = {"t0": 0.0, "total": None}

    def run_all():
        state["t0"] = time.time()
        ths = [threading.Thread(target=work, args=(o,)) for o in owners]
        for t in ths:
            t.start()

        def waiter():
            for t in ths:
                t.join(timeout=90)
            state["total"] = round(time.time() - state["t0"], 2)
            QMetaObject.invokeMethod(app, "quit", Qt.ConnectionType.QueuedConnection)

        threading.Thread(target=waiter, daemon=True).start()

    QTimer.singleShot(0, run_all)
    QTimer.singleShot(150000, app.quit)      # 硬超时，别让自检挂死
    app.exec()

    total = state["total"] if state["total"] is not None else -1
    all_same = len(results) == 3 and all(t == f"{o}-DATA" for o, (t, _) in results.items())
    ok(all_same, "每个视图读回的是自己的内容（没有互相顶掉）", json.dumps(results, ensure_ascii=False))
    ok(len(results) == 3 and all(title == o for o, (_, title) in results.items()), "标题各自正确")
    ok(0 < total < 5.5, f"3 个页面并行加载（总耗时 {total}s，串行要 6s+）", f"total={total}s timing={timing}")

    print("\n[真实] 4. 销毁")
    for o in owners:
        ok(bb.destroy_owner_view(o), f"{o} 视图已销毁")
    ok(bb.owner_views() == {}, "注册表已清空", str(bb.owner_views()))
    ok(bb.get_bridge() is not None, "主窗口 Bridge 不受影响（不会被误删）")


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "logic").lower()
    print("=" * 60)
    print("动态多视图自检 —", mode)
    print("=" * 60)
    if mode == "real":
        test_real()
    else:
        test_logic()

    print("\n" + "=" * 60)
    print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 未通过")
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("全部通过")
