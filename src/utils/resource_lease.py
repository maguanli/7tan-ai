# -*- coding: utf-8 -*-
"""命名资源租约 —— 给「进程内只有一份」的东西排队。

实测到的真实冲突（tools/concurrency_probe.py，2026-11-01）：

    L3-1  浏览器 4 个模块级状态对象跨线程同一实例；
          Worker A 把 _active_ctx 设成 source，Worker B 切成 admin，
          A 下一次操作看到的是 admin —— 它操作了错误的窗口，而且不会报错。
    L3-1  desktop_bot 插件内无任何 Lock，鼠标键盘只有一套。
    L1-4  同一文件朴素读-改-写，8 线程 × 40 轮丢 97% 的更新。
    L1-5  同一仓库并发 git 写操作，17/24 次撞 index.lock。

这些不是「配置调一调」能解决的，必须有人排队。

设计取舍：
    ① 按名字排队，不按工具排队。
       "browser" / "desktop" / "camera" / "file:<绝对路径>" / "git:<仓库根>"
       同一名字同一时刻只有一个持有人。

    ② 持有人重入不互锁。
       同一个 Worker 连续调两次 browse_page，不该自己把自己锁死。

    ③ 粘性租约（sticky）解决「状态跨调用残留」。
       浏览器的问题是 _active_ctx 会在两次调用之间被人改掉，
       所以光给单次调用加锁不够 —— 必须由同一持有人从第一次用浏览器
       一直占到 Worker 结束。acquire(sticky=True) 就是这个语义。

    ④ 等不到就拒绝，不静默降级。
       超时返回 LeaseTimeout，调用方把「谁占着、等了多久」写回给模型，
       而不是让命令悄悄在错误状态下执行。

    ⑤ 记录持有时间，超过 max_hold 打警告但不强抢。
       强抢会让正在跑的浏览器操作被打断，比等更糟。
       真正的兜底是 Worker 结束时 release_all(owner)。
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager

__all__ = [
    "LeaseTimeout",
    "Lease",
    "acquire",
    "release",
    "release_all",
    "guard",
    "status",
    "holder_of",
    "stats",
]

_cv = threading.Condition()
_held: dict = {}          # name -> Lease


class LeaseTimeout(Exception):
    """等待资源超时（资源被别的持有人占着）。"""

    def __init__(self, name: str, holder: str, waited: float):
        self.name = name
        self.holder = holder
        self.waited = waited
        super().__init__(
            f"资源 {name} 正被 {holder} 占用，已等待 {waited:.0f}s 仍未释放"
        )


class Lease:
    __slots__ = ("name", "owner", "sticky", "acquired_at", "depth", "note")

    def __init__(self, name: str, owner: str, sticky: bool = False, note: str = ""):
        self.name = name
        self.owner = owner
        self.sticky = bool(sticky)
        self.acquired_at = time.time()
        self.depth = 1              # 重入计数
        self.note = note

    def held_for(self) -> float:
        return time.time() - self.acquired_at

    def __repr__(self) -> str:
        return (f"<Lease {self.name} owner={self.owner} sticky={self.sticky} "
                f"held={self.held_for():.1f}s depth={self.depth}>")


def acquire(name: str, owner: str, timeout: float = 180.0,
            sticky: bool = False, max_hold: float = 900.0) -> Lease:
    """申请一个命名资源。拿不到抛 LeaseTimeout。

    timeout  ：最多等多久（秒），None = 一直等
    sticky   ：True 时同一 owner 后续 acquire 直接重入，直到 release_all
    """
    name = str(name)
    owner = str(owner or "main")
    t0 = time.time()
    deadline = None if timeout is None else (t0 + float(timeout))

    with _cv:
        while True:
            cur = _held.get(name)
            if cur is None:
                lease = Lease(name, owner, sticky=sticky)
                _held[name] = lease
                return lease

            if cur.owner == owner:                       # 重入
                cur.depth += 1
                if sticky:
                    cur.sticky = True
                return cur

            now = time.time()
            if max_hold and cur.held_for() > max_hold:
                # 只警告不强抢：强抢会打断正在跑的浏览器操作
                import logging
                logging.getLogger(__name__).warning(
                    f"资源 {name} 被 {cur.owner} 持有 {cur.held_for():.0f}s，"
                    f"超过 max_hold={max_hold}s —— 检查该 Worker 是否卡死"
                )

            if deadline is not None and now >= deadline:
                raise LeaseTimeout(name, cur.owner, now - t0)

            wait = 0.05 if deadline is None else max(0.01, min(0.2, deadline - now))
            _cv.wait(wait)


def release(lease: Lease) -> None:
    """释放（重入计数减一，归零才真正让出）。"""
    if lease is None:
        return
    with _cv:
        cur = _held.get(lease.name)
        if cur is None or cur is not lease:
            return
        cur.depth -= 1
        if cur.depth <= 0:
            _held.pop(lease.name, None)
            _cv.notify_all()


def release_all(owner: str) -> list:
    """释放某持有人的全部资源（含重入未归零的）。

    Worker 结束时必须调用：否则一个异常退出就会把浏览器永久占住。
    """
    owner = str(owner or "main")
    freed = []
    with _cv:
        for name, lease in list(_held.items()):
            if lease.owner == owner:
                _held.pop(name, None)
                freed.append(name)
        if freed:
            _cv.notify_all()
    return freed


@contextmanager
def guard(name: str, owner: str, timeout: float = 180.0, sticky: bool = False):
    """申请 → 执行 → 释放。

    sticky=True 时【不】在退出时释放：这正是粘性租约的意义。
    浏览器 / 桌面这类资源的状态（_active_ctx、鼠标焦点）会跨调用残留，
    如果每次调用结束就放开，两次调用之间别人一插进来，下一次调用就会
    操作到错误的目标 —— 而且不会报错。

    粘性租约由 release_all(owner) 统一回收（spawn_worker 的 finally 里调）。
    万一调用方忘了回收，acquire 里的 max_hold 会打警告，不会静默烂掉。
    """
    lease = acquire(name, owner, timeout=timeout, sticky=sticky)
    try:
        yield lease
    finally:
        if not sticky:
            release(lease)


def holder_of(name: str):
    with _cv:
        cur = _held.get(name)
        return cur.owner if cur else None


def status() -> dict:
    """当前被占用的资源清单（供诊断工具回显）。"""
    with _cv:
        return {
            name: {
                "owner": l.owner,
                "held_s": round(l.held_for(), 1),
                "sticky": l.sticky,
                "depth": l.depth,
            }
            for name, l in _held.items()
        }


def stats() -> dict:
    s = status()
    return {"held": len(s), "detail": s}
