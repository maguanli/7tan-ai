"""状态快照瘦身 + 恢复重建 —— 「越抓越慢」性能修复的回归哨兵。

背景（实测数据，勿回退）
-----------------------
早期版本把 visited / queue / saved 三个全量集合一并写进 _mirror_state.json。
实测 youbian 任务跑到 28.5 万 URL 时，快照达 87.2 MB，json.dumps 单次 1.34 秒，
且序列化发生在**事件循环线程**上 —— 每 5 秒把 8 个 worker 全部冻结 1.34 秒
（占空比 27%），并且体积随抓取量持续增长，于是「越抓越慢」。

本测试锁死两件事：
  1. 快照体积/耗时与抓取量无关（只留小标量）；
  2. 恢复时 visited / saved / pending 都能从「清单 + 流水账」精确重建。
"""
import asyncio
import json
import os
import time

from app.crawler import CrawlConfig, Mirror


def _mk(tmp_path, **kw) -> tuple[Mirror, str]:
    out = str(tmp_path)
    cfg = CrawlConfig(start_url="http://x.test/", out_root=out, resume=True, **kw)
    m = Mirror(cfg)
    m.queue = asyncio.Queue()
    return m, out


def test_snapshot_size_is_independent_of_crawl_size(tmp_path):
    """快照必须只含小标量：塞进 10 万 visited + 30 万 pending 也不许变大。"""
    m, out = _mk(tmp_path)
    n = 100_000
    m._visited = {f"http://x.test/p{i}.html" for i in range(n)}
    m._pending = {
        f"http://x.test/q{i}.html": {"url": f"http://x.test/q{i}.html",
                                     "depth": 1, "kind": "page"}
        for i in range(n * 3)
    }
    m._saved = {f"http://x.test/p{i}.html": f"p{i}.html" for i in range(n)}

    t0 = time.time()
    asyncio.run(m._save_state(force=True))
    dt = time.time() - t0

    path = os.path.join(out, "_mirror_state.json")
    size = os.path.getsize(path)
    obj = json.load(open(path, encoding="utf-8"))

    # 若把三个全量集合写回去，这里是几十 MB / 1 秒级
    assert size < 200 * 1024, f"状态快照过大：{size / 1024:.1f} KB（应稳定在 KB 级）"
    assert dt < 0.30, f"快照写入过慢：{dt:.3f}s（不得阻塞事件循环）"
    for bad in ("visited", "queue", "saved"):
        assert bad not in obj, f"快照仍内嵌全量字段 {bad}"
    # 但计数要如实反映内存中的真实规模
    assert obj["visited_count"] == n
    assert obj["pending_count"] == n * 3


def test_snapshot_throttled_after_first_save(tmp_path):
    """非 force 的重复调用必须被节流直接挡回（不再争抢锁）。"""
    m, out = _mk(tmp_path)
    asyncio.run(m._save_state(force=True))
    mtime1 = os.path.getmtime(os.path.join(out, "_mirror_state.json"))
    time.sleep(0.05)
    asyncio.run(m._save_state())          # 节流窗口内 → 应直接返回
    mtime2 = os.path.getmtime(os.path.join(out, "_mirror_state.json"))
    assert mtime1 == mtime2, "节流窗口内的 _save_state() 不应写盘"


def test_restore_rebuilds_visited_saved_pending(tmp_path):
    """恢复：pending = 流水账 − 已落盘；visited / saved 由清单重建。"""
    m, out = _mk(tmp_path)

    # 清单：3 个页面已落盘
    with open(os.path.join(out, "_mirror_manifest.ndjson"), "w", encoding="utf-8") as f:
        for i in range(3):
            f.write("\n" + json.dumps({
                "url": f"http://x.test/p{i}.html",
                "path": f"x.test/p{i}.html",
                "size": 10, "content_type": "text/html", "status": 200,
            }, ensure_ascii=False))

    # 流水账：3 个已落盘 + 2 个待抓
    with open(os.path.join(out, "_mirror_queue.ndjson"), "w", encoding="utf-8") as f:
        for i in range(3):
            f.write(f"\n0\tpage\thttp://x.test/p{i}.html")
        for i in range(2):
            f.write(f"\n1\tpage\thttp://x.test/q{i}.html")

    # 瘦身后的状态文件（已不含全量集合）
    state = {"version": 2, "start_url": "http://x.test/", "done": False,
             "visited_count": 3, "pending_count": 2, "stats": {}, "errors": []}
    m._restore_state(state)

    assert m._resumed is True
    # visited 由清单重建
    assert "http://x.test/p0.html" in m._visited
    # saved（URL → 本地路径）由清单重建，供续抓后继续改写链接
    assert m._saved.get("http://x.test/p0.html") == "x.test/p0.html"
    assert m._saved.get("http://x.test/p2.html") == "x.test/p2.html"
    # pending = 流水账 − 已落盘
    assert set(m._pending) == {"http://x.test/q0.html", "http://x.test/q1.html"}
    # 待抓的不应被视为已访问
    for u in m._pending:
        assert u not in m._visited
    # 计数从清单精确重算
    assert m.stats["files"] == 3
    assert m.stats["pages_ok"] == 3


def test_restore_accepts_legacy_snapshot(tmp_path):
    """旧版状态文件（内嵌全量集合）仍须能续抓 —— 向后兼容。"""
    m, out = _mk(tmp_path)
    legacy = {
        "start_url": "http://x.test/",
        "visited": ["http://x.test/p0.html", "http://x.test/p1.html"],
        "queue": [{"url": "http://x.test/q0.html", "depth": 1, "kind": "page"}],
        "inflight": [{"url": "http://x.test/inflight.html", "depth": 1, "kind": "page"}],
        "saved": {"http://x.test/p0.html": "x.test/p0.html"},
        "stats": {"pages_ok": 2, "files": 2, "bytes": 20, "started_at": 1.0},
        "errors": [],
    }
    m._restore_state(legacy)
    assert "http://x.test/p0.html" in m._visited
    assert m._saved.get("http://x.test/p0.html") == "x.test/p0.html"
    # 在途任务应被剔除 visited 并重新入队
    assert "http://x.test/inflight.html" in m._pending
    assert "http://x.test/inflight.html" not in m._visited
